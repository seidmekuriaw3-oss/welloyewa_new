---
name: Wolloyewa Store Bot startup configuration
description: How to start the bot, what env vars are needed, and what is non-fatal
---

## Workflow command
```
DATABASE_URL='postgresql://postgres:password@helium/heliumdb?sslmode=disable' ENVIRONMENT=development DEBUG=True ENABLE_WEB_APP=False PROMETHEUS_ENABLED=False LOG_FORMAT=text LOG_FILE_PATH=./logs/bot_errors.log REDIS_URL=redis://localhost:6379/0 CELERY_BROKER_URL=redis://localhost:6379/0 CELERY_RESULT_BACKEND=redis://localhost:6379/0 CELERY_TASK_ALWAYS_EAGER=True ADMIN_IDS=5848843259 uvicorn main:app --host 0.0.0.0 --port 8000
```
Port 8000, outputType "console".

## Non-fatal startup items
- Redis: optional, log warning if unavailable
- Celery/scheduler: optional, log warning if unavailable

## ENCRYPTION_KEY
Must be a valid Fernet key (32 url-safe base64-encoded bytes). Generate with:
`python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"`
Set in shared env vars.

## ENABLE_WEB_APP
Must be False — the web_app router has broken imports not worth fixing.

## DATABASE_URL handling
The URL has `sslmode=disable` which asyncpg doesn't accept. Stripped in session.py with regex before creating engine.
