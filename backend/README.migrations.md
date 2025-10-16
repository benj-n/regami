# Database migrations (Alembic)

This project uses Alembic for schema migrations.

## Setup

- Ensure dependencies are installed (alembic, SQLAlchemy).
- Set `DATABASE_URL` in your environment, e.g. `sqlite:///./regami.db` or a PostgreSQL URL.

## Commands

- Generate a new migration from models:

```bash
cd backend
alembic -c alembic.ini revision --autogenerate -m "describe change"
```

- Apply migrations:

```bash
cd backend
alembic -c alembic.ini upgrade head
```

- Downgrade one step:

```bash
cd backend
alembic -c alembic.ini downgrade -1
```

## Notes

- App startup DB reset is controlled by env var `RESET_DB_ON_STARTUP` (default True). Set to `False` in non-dev to preserve data and rely on Alembic.
- For autogenerate to detect changes, ensure that `app.models` are importable and `DATABASE_URL` points to the target DB.
