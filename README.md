# GymApp Django Project

This repository contains a basic Django project scaffold for a future Gym application.

## Setup

1. **Create and activate a virtual environment** (recommended):

```bash
python3 -m venv .venv
source .venv/bin/activate
```

2. **Install dependencies**:

```bash
pip install -r requirements.txt
```

3. **Run database migrations**:

```bash
python manage.py migrate
```

4. **Start the development server**:

```bash
python manage.py runserver
```

### Auth API

Base path: `/api/auth/`

- **Signup**: `POST /api/auth/signup/`
  - Body: `{"username": "...", "email": "...", "password": "..." }`
  - Response: user info + `access` and `refresh` tokens.

- **Login**: `POST /api/auth/login/`
  - Body: `{"username": "...", "password": "..." }`
  - Response: user info + `access` and `refresh` tokens.

- **Forgot password**: `POST /api/auth/forgot-password/`
  - Body: `{"email": "..." }`
  - Response: generic message; no email is actually sent yet.

- **Refresh access token**: `POST /api/auth/refresh/`
  - Body: `{"refresh": "<refresh_token>" }`
  - Response: new `access` token if refresh token is valid.


