# Kanban Task Management API

This is a Django REST API for a Kanban-style task management application.

## Features

- JWT authentication with registration and login
- User profile management
- Workspace creation and membership management
- Boards and columns with task movement
- Task comments and activity logs
- Dashboard statistics and analytics
- PostgreSQL database support
- DRF pagination and filters

## Requirements

- Python 3.10+
- PostgreSQL
- Docker (optional)

## Local setup

1. Create a Python virtual environment:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Set environment variables in a `.env` file at the project root:
   ```env
   SECRET_KEY=replace-this-with-a-secure-secret
   DEBUG=True
   ALLOWED_HOSTS=127.0.0.1,localhost
   DATABASE_URL=postgres://kanban_user:Neema@123@localhost:5432/kanban
   ```

4. Run migrations:
   ```bash
   python manage.py migrate
   ```

5. Create a superuser:
   ```bash
   python manage.py createsuperuser
   ```

6. Run the development server:
   ```bash
   python manage.py runserver
   ```

## Docker setup

Build and run with Docker Compose:

```bash
docker compose up --build
```

Then open `http://localhost:8000`.

## Render deployment

### 1. Create a new web service on Render
- Choose `Web Service`.
- Connect your GitHub repository.
- Set the branch to deploy.

### 2. Set the build command

```bash
pip install -r requirements.txt
```

### 3. Set the start command

```bash
gunicorn kanbanproject.wsgi:application --bind 0.0.0.0:8000 --workers 3
```

### 4. Add environment variables on Render
- `SECRET_KEY` — secure random string
- `DEBUG` — `False`
- `ALLOWED_HOSTS` — e.g. `your-service.onrender.com`
- `DATABASE_URL` — Render PostgreSQL connection URL
- `DATABASE_SSL` — `True` (if Render requires SSL)

### 5. Configure PostgreSQL
- Create a managed PostgreSQL database on Render.
- Copy the provided database URL into `DATABASE_URL`.

### 6. Deploy
- Trigger a deploy from Render.
- Once deployed, run migrations via Render shell or deploy command:
  ```bash
  python manage.py migrate
  ```

## Notes

- `venv/` is ignored by `.gitignore`.
- Static files are served with WhiteNoise.
- On Render, make sure `DEBUG=False` for production.
# Refresh contributors
