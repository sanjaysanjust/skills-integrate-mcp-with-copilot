"""Credential and signed-session helpers for teacher access."""

import base64
import hashlib
import hmac
import json
import os
import secrets
import time
from pathlib import Path
from typing import Any

PASSWORD_HASH_ITERATIONS = 600_000
SESSION_DURATION_SECONDS = 8 * 60 * 60
SESSION_COOKIE_NAME = "teacher_session"
TEACHER_FILE = Path(__file__).with_name("teachers.json")


class CredentialConfigurationError(Exception):
    """Raised when teacher credentials cannot be loaded safely."""


def _encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode("ascii")


def _decode(value: str) -> bytes:
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))


def hash_password(password: str) -> dict[str, str]:
    salt = secrets.token_bytes(16)
    password_hash = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt, PASSWORD_HASH_ITERATIONS
    )
    return {"salt": _encode(salt), "password_hash": _encode(password_hash)}


def load_teacher_credentials(path: Path = TEACHER_FILE) -> dict[str, Any]:
    try:
        with path.open(encoding="utf-8") as credentials_file:
            credentials = json.load(credentials_file)
    except FileNotFoundError as error:
        raise CredentialConfigurationError(
            "Teacher credentials are not configured"
        ) from error
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise CredentialConfigurationError(
            "Teacher credentials could not be read"
        ) from error

    teachers = credentials.get("teachers") if isinstance(credentials, dict) else None
    if not isinstance(teachers, dict) or not teachers:
        raise CredentialConfigurationError(
            "Teacher credentials file must contain at least one teacher"
        )
    for username, record in teachers.items():
        if (
            not isinstance(username, str)
            or not isinstance(record, dict)
            or not isinstance(record.get("salt"), str)
            or not isinstance(record.get("password_hash"), str)
        ):
            raise CredentialConfigurationError(
                "Teacher credentials file contains an invalid record"
            )
        try:
            salt = _decode(record["salt"])
            password_hash = _decode(record["password_hash"])
        except (ValueError, TypeError) as error:
            raise CredentialConfigurationError(
                "Teacher credentials file contains an invalid record"
            ) from error
        if len(salt) != 16 or len(password_hash) != 32:
            raise CredentialConfigurationError(
                "Teacher credentials file contains an invalid record"
            )
    return teachers


def verify_teacher_password(
    username: str, password: str, path: Path = TEACHER_FILE
) -> bool:
    teachers = load_teacher_credentials(path)
    record = teachers.get(username)
    if record is None:
        return False

    try:
        salt = _decode(record["salt"])
        expected_hash = _decode(record["password_hash"])
    except (ValueError, TypeError) as error:
        raise CredentialConfigurationError(
            "Teacher credentials file contains an invalid record"
        ) from error

    actual_hash = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt, PASSWORD_HASH_ITERATIONS
    )
    return secrets.compare_digest(actual_hash, expected_hash)


def get_session_secret() -> bytes:
    secret = os.environ.get("SESSION_SECRET", "")
    if len(secret.encode("utf-8")) < 32:
        raise CredentialConfigurationError(
            "SESSION_SECRET must be set to at least 32 characters"
        )
    return secret.encode("utf-8")


def create_session_token(
    username: str, secret: bytes, now: int | None = None
) -> str:
    issued_at = int(time.time()) if now is None else now
    payload = json.dumps(
        {"username": username, "expires": issued_at + SESSION_DURATION_SECONDS},
        separators=(",", ":"),
    ).encode("utf-8")
    encoded_payload = _encode(payload)
    signature = hmac.new(
        secret, encoded_payload.encode("ascii"), hashlib.sha256
    ).digest()
    return f"{encoded_payload}.{_encode(signature)}"


def verify_session_token(
    token: str | None, secret: bytes, now: int | None = None
) -> str | None:
    if not token:
        return None

    try:
        encoded_payload, encoded_signature = token.split(".", maxsplit=1)
        signature = _decode(encoded_signature)
        expected_signature = hmac.new(
            secret, encoded_payload.encode("ascii"), hashlib.sha256
        ).digest()
        if not hmac.compare_digest(signature, expected_signature):
            return None
        payload = json.loads(_decode(encoded_payload))
    except (ValueError, TypeError, UnicodeDecodeError, json.JSONDecodeError):
        return None

    expires = payload.get("expires") if isinstance(payload, dict) else None
    username = payload.get("username") if isinstance(payload, dict) else None
    current_time = int(time.time()) if now is None else now
    if (
        not isinstance(username, str)
        or not username
        or not isinstance(expires, int)
        or expires <= current_time
    ):
        return None
    return username
