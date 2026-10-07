import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from auth import (  # noqa: E402
    SESSION_DURATION_SECONDS,
    create_session_token,
    hash_password,
    verify_session_token,
    verify_teacher_password,
)
from app import LoginRequest, app, login, require_teacher  # noqa: E402
from fastapi import HTTPException  # noqa: E402
from fastapi import Response  # noqa: E402
from starlette.requests import Request  # noqa: E402


class TeacherAuthTests(unittest.TestCase):
    def test_password_hash_authenticates_without_storing_plaintext(self):
        password = "a-long-teacher-password"
        record = hash_password(password)
        with tempfile.TemporaryDirectory() as directory:
            credentials_path = Path(directory) / "teachers.json"
            credentials_path.write_text(
                json.dumps({"teachers": {"teacher1": record}}), encoding="utf-8"
            )

            self.assertNotIn(password, credentials_path.read_text(encoding="utf-8"))
            self.assertTrue(
                verify_teacher_password("teacher1", password, credentials_path)
            )
            self.assertFalse(
                verify_teacher_password(
                    "teacher1", "incorrect-password", credentials_path
                )
            )
            self.assertFalse(
                verify_teacher_password("missing", password, credentials_path)
            )

    def test_session_tokens_reject_tampering_and_expiration(self):
        secret = b"s" * 32
        token = create_session_token("teacher1", secret, now=100)

        self.assertEqual(verify_session_token(token, secret, now=101), "teacher1")
        self.assertIsNone(
            verify_session_token(token + "tampered", secret, now=101)
        )
        self.assertIsNone(
            verify_session_token(token, secret, now=100 + SESSION_DURATION_SECONDS)
        )

    def test_teacher_dependency_requires_a_valid_session_cookie(self):
        secret = "a-session-secret-that-is-at-least-32-characters"
        request_scope = {
            "type": "http",
            "method": "POST",
            "path": "/activities/Chess%20Club/signup",
            "query_string": b"",
            "headers": [],
            "server": ("testserver", 80),
            "client": ("testclient", 123),
            "scheme": "http",
        }

        with patch.dict(os.environ, {"SESSION_SECRET": secret}):
            with self.assertRaises(HTTPException) as error:
                require_teacher(Request(request_scope))
            self.assertEqual(error.exception.status_code, 401)

            token = create_session_token("teacher1", secret.encode("utf-8"))
            authenticated_scope = {
                **request_scope,
                "headers": [
                    (b"cookie", f"teacher_session={token}".encode("ascii"))
                ],
            }
            with patch("app.load_teacher_credentials", return_value={"teacher1": {}}):
                self.assertEqual(
                    require_teacher(Request(authenticated_scope)), "teacher1"
                )

            with patch("app.load_teacher_credentials", return_value={}):
                with self.assertRaises(HTTPException) as revoked_error:
                    require_teacher(Request(authenticated_scope))
                self.assertEqual(revoked_error.exception.status_code, 401)

    def test_signup_and_unregister_routes_require_teacher_dependency(self):
        protected_routes = {
            "/activities/{activity_name}/signup",
            "/activities/{activity_name}/unregister",
        }
        routes = {route.path: route for route in app.routes}

        for path in protected_routes:
            with self.subTest(path=path):
                dependencies = routes[path].dependant.dependencies
                self.assertTrue(
                    any(dependency.call is require_teacher for dependency in dependencies)
                )

    def test_login_sets_http_only_signed_session_cookie(self):
        secret = b"s" * 32
        response = Response()
        with (
            patch("app.get_session_secret", return_value=secret),
            patch("app.verify_teacher_password", return_value=True),
        ):
            result = login(LoginRequest(username="teacher1", password="password"), response)

        self.assertEqual(result["message"], "Signed in successfully")
        cookie = response.headers["set-cookie"]
        self.assertIn("HttpOnly", cookie)
        self.assertIn("SameSite=strict", cookie)
        self.assertIn("Max-Age=28800", cookie)

    def test_login_rejects_invalid_credentials(self):
        response = Response()
        with (
            patch("app.get_session_secret", return_value=b"s" * 32),
            patch("app.verify_teacher_password", return_value=False),
        ):
            with self.assertRaises(HTTPException) as error:
                login(
                    LoginRequest(username="teacher1", password="incorrect"),
                    response,
                )

        self.assertEqual(error.exception.status_code, 401)
        self.assertNotIn("set-cookie", response.headers)


if __name__ == "__main__":
    unittest.main()
