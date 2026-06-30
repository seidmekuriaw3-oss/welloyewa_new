---
name: Wolloyewa Store Bot startup configuration
description: How to start the bot, what env vars are needed, known fixes, and what is non-fatal
---

## Workflow command
```
uvicorn main:app --host 0.0.0.0 --port 5000
```
Port 5000, outputType "webview".

## Replit-managed DB
DATABASE_URL is injected by Replit runtime. Do NOT set POSTGRES_* vars manually — DATABASE_URL from secret takes precedence. sslmode is stripped in session.py before asyncpg use.

## Required secrets (all set in Replit Secrets)
- TELEGRAM_BOT_TOKEN — full bot token from @BotFather
- ENCRYPTION_KEY — valid Fernet key (44 chars). Generate: `python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"`
- SECRET_KEY — random secret for app security
- JWT_SECRET_KEY — random secret for JWT signing

## Non-fatal startup items
- Redis: optional, log warning if unavailable — falls back to JSONFilePersistence for bot state
- Celery/scheduler: optional, CELERY_TASK_ALWAYS_EAGER=True runs tasks inline

## Package installs (use pip, NOT poetry)
Poetry has no lock file and conflicts with Replit's package manager. All packages installed via `pip install` into `.pythonlibs`. Key packages: fastapi, uvicorn[standard], python-telegram-bot[job-queue], sqlalchemy, asyncpg, alembic, redis, cryptography, python-jose[cryptography], passlib[bcrypt], pydantic-settings, python-json-logger, psutil, aioboto3, celery.

## pythonjsonlogger v4 breaking change
Old: `import pythonjsonlogger.jsonlogger` / `from pythonjsonlogger.jsonlogger import JsonFormatter`
New: `from pythonjsonlogger import json as jsonlogger` / `from pythonjsonlogger.json import JsonFormatter`
Fixed in: `core/logger.py`

## Telegram Conflict error fix
Before `start_polling`, always: `await bot.delete_webhook(drop_pending_updates=True)` then `await asyncio.sleep(2)`.
**Why:** On restart, the previous polling session may still be alive at Telegram's end for ~30s. delete_webhook clears it immediately.
Fixed in: `main.py` lifespan startup block.

## Correct bot shutdown sequence
1. `await updater.stop()` (if updater.running)
2. `await application.stop()` (if application.running)
3. `await application.shutdown()`

## CORS / TrustedHostMiddleware
CORS_ALLOWED_ORIGINS and ALLOWED_HOSTS both default to ["*"] for Replit compatibility.
**Why:** Replit proxies requests through its own domains — restricting hosts breaks the webview and API.

## FastAPI `regex` → `pattern`
Fixed in: analytics.py, admin.py, dashboards.py endpoint files.

## Logs directory
`os.makedirs("./logs", exist_ok=True)` added at top of `main.py` before setup_logging() — prevents FileNotFoundError.

## alembic.ini
sqlalchemy.url is a fallback only — alembic/env.py reads DATABASE_URL from env. Set to a harmless placeholder.

## Cleaned hardcoded values in core/config.py
- POSTGRES_PASSWORD: now empty string default
- TELEGRAM_BOT_TOKEN: now empty string default (must be set via Replit Secret)
- CORS_ALLOWED_ORIGINS: now ["*"]
- ALLOWED_HOSTS: now ["*"]

## Missing packages added
- psutil — used in core/monitoring/health_checks.py
- aioboto3 — used in infrastructure/storage/s3_provider.py
- python-json-logger — used in core/logger.py

## Test directory typo fixed
tests/test_ integration/ (with space) → tests/test_integration_flow/

## ENABLE_WEB_APP
Keep False — the web_app router has unresolved import issues.
