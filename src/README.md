# Mergington High School Activities API

A super simple FastAPI application that allows students to view and sign up for extracurricular activities.

## Features

- View all available extracurricular activities
- View registered participants without signing in
- Allow authenticated teachers to manage activity registrations

## Teacher access

Teacher accounts are stored locally in `src/teachers.json`. Passwords are
stored as salted PBKDF2 hashes, not plaintext, and the file is ignored by Git.
Create an account interactively with:

```sh
cd src
python manage_teachers.py
```

The script prompts for a username and password (at least 12 characters). Run it
once for each teacher. Keep the credential file private and provision it on the
server; it is not included in the repository.

Set `SESSION_SECRET` to a randomly generated value of at least 32 characters
before starting the app. For a local shell, generate and export one with:

```sh
export SESSION_SECRET="$(python -c 'import secrets; print(secrets.token_urlsafe(48))')"
```

Set `COOKIE_SECURE=true` when serving the app over HTTPS. The app uses signed,
HttpOnly, SameSite=Strict session cookies that expire after eight hours.
Without teacher credentials or a session secret, management endpoints fail
closed and sign-in is unavailable.

## Getting Started

1. Install the dependencies:

   ```
   pip install -r ../requirements.txt
   ```

2. Create at least one teacher account and configure a session-signing secret as
   described in [Teacher access](#teacher-access).

3. Run the application from the `src` directory:

   ```
   uvicorn app:app --reload
   ```

4. Open your browser and go to:
   - API documentation: http://localhost:8000/docs
   - Alternative documentation: http://localhost:8000/redoc

## API Endpoints

| Method | Endpoint                                                          | Description                                                         |
| ------ | ----------------------------------------------------------------- | ------------------------------------------------------------------- |
| GET    | `/activities`                                                     | Get all activities with their details and current participant count |
| POST   | `/auth/login`                                                      | Sign in as a teacher (JSON username and password)                   |
| GET    | `/auth/status`                                                     | Check whether the current browser is signed in                      |
| POST   | `/auth/logout`                                                     | Sign out and clear the session cookie                               |
| POST   | `/activities/{activity_name}/signup?email=student@mergington.edu` | Teacher-only registration                                           |
| DELETE | `/activities/{activity_name}/unregister?email=student@mergington.edu` | Teacher-only unregistration                                      |

## Data Model

The application uses a simple data model with meaningful identifiers:

1. **Activities** - Uses activity name as identifier:

   - Description
   - Schedule
   - Maximum number of participants allowed
   - List of student emails who are signed up

2. **Students** - Uses email as identifier:
   - Name
   - Grade level

All data is stored in memory, which means data will be reset when the server restarts.
