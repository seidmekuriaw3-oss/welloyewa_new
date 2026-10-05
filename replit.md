# Wolloyewa Store Bot

Ethiopian e-commerce Telegram bot with multi-vendor support. Built with FastAPI + python-telegram-bot + PostgreSQL + Redis.

## Stack
- **Python 3.11**
- **FastAPI** (REST API + webhook receiver) on port **5000**
- **python-telegram-bot v20+** (polling or webhook)
- **SQLAlchemy 2 + asyncpg** (async PostgreSQL)
- **Alembic** (migrations)
- **Celery + Redis** (background tasks — optional, non-fatal if Redis unavailable)

## Running the app

```
bash start.sh
```

Workflow: **Start application** (port 5000, webview output). The script starts Redis and then runs Uvicorn.

## Required secrets / env vars

| Key | Where | Notes |
|-----|-------|-------|
| `TELEGRAM_BOT_TOKEN` | Replit Secret | Required to enable Telegram bot polling; the web storefront can load without it. |
| `ENCRYPTION_KEY` | Replit Secret | Required in production. Development creates and persists a local key automatically. |

## Environment variables (shared)

Set in `.replit` / Replit env panel:

| Key | Value | Notes |
|-----|-------|-------|
| `ENVIRONMENT` | `development` | |
| `DEBUG` | `True` | |
| `ENABLE_WEB_APP` | `True` | Web app live at `/app/` — all import & routing issues resolved |
| `PROMETHEUS_ENABLED` | `False` | |
| `LOG_FORMAT` | `text` | `json` only used in production |
| `LOG_FILE_PATH` | `./logs/bot_errors.log` | |
| `CELERY_TASK_ALWAYS_EAGER` | `True` | Runs Celery tasks inline without a broker |
| `ADMIN_IDS` | `<your telegram user ID>` | Comma-separated Telegram user IDs for admins |

## Database

Uses Replit's managed PostgreSQL (`helium`). `DATABASE_URL` is injected automatically by Replit — do not set it manually.

Run migrations:
```
alembic upgrade head
```

## Known non-fatal startup items

- **Redis** — optional; app warns and continues if unavailable
- **Celery / scheduler** — optional; `CELERY_TASK_ALWAYS_EAGER=True` runs tasks inline
- **Telegram bot** — if `TELEGRAM_BOT_TOKEN` is absent, bot startup is skipped and the web storefront remains available.
- **ENCRYPTION_KEY** — development uses a persistent local key; production requires a valid Fernet key.

## Key import fixes (previous session)

See `.agents/memory/wolloyewa-import-fixes.md` for the full list of import errors that were fixed during initial setup.

## User preferences

- `ENABLE_WEB_APP=True` — web_app router is working; templates directory created at `bot/web_app/templates/`
