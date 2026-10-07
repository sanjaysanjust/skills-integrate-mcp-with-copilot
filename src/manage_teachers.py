"""Interactively add teachers to the local credential file."""

import getpass
import json
import os

from auth import (
    TEACHER_FILE,
    CredentialConfigurationError,
    hash_password,
    load_teacher_credentials,
)


def main() -> None:
    username = input("Teacher username: ").strip()
    if not username:
        raise SystemExit("Username cannot be empty.")

    try:
        teachers = load_teacher_credentials()
    except CredentialConfigurationError as error:
        if TEACHER_FILE.exists():
            raise SystemExit(str(error)) from error
        teachers = {}

    if username in teachers:
        raise SystemExit(f"Teacher {username!r} already exists.")

    password = getpass.getpass("Teacher password (at least 12 characters): ")
    if len(password) < 12:
        raise SystemExit("Password must be at least 12 characters.")
    if password != getpass.getpass("Confirm password: "):
        raise SystemExit("Passwords do not match.")

    teachers[username] = hash_password(password)
    descriptor = os.open(
        TEACHER_FILE, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600
    )
    with os.fdopen(descriptor, "w", encoding="utf-8") as credentials_file:
        json.dump({"teachers": teachers}, credentials_file, indent=2)
        credentials_file.write("\n")
    os.chmod(TEACHER_FILE, 0o600)
    print(f"Added teacher {username!r} to {TEACHER_FILE}.")


if __name__ == "__main__":
    main()
