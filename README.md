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

### Documentation

- **[API.md](API.md)** — full API reference (paths, methods, auth, bodies, responses).
- **[DB.md](DB.md)** — database schema, tables, and relationships.

Copy **`.env.example`** to **`.env`** and set secrets (see file comments). Never commit `.env`.


