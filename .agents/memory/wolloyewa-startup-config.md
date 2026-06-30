---
name: Wolloyewa Store Bot startup configuration
description: How to start the bot, what env vars are needed, and what is non-fatal
---

## Workflow command
```
uvicorn main:app --host 0.0.0.0 --port 8000
```
Port 8000, outputType "console".

## Replit-managed DB
DATABASE_URL is injected by Replit runtime pointing to `helium` (postgres). Do NOT set POSTGRES_* vars — they conflict. DATABASE_URL is stripped of sslmode in session.py before asyncpg use.

## Required secrets
- TELEGRAM_BOT_TOKEN — full bot token from @BotFather (format: `<digits>:<string>`)
- ENCRYPTION_KEY — valid Fernet key (44 chars). Generate: `python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"`

## Non-fatal startup items
- Redis: optional, log warning if unavailable
- Celery/scheduler: optional, CELERY_TASK_ALWAYS_EAGER=True runs tasks inline

## ENCRYPTION_KEY
Must be a valid Fernet key (32 url-safe base64-encoded bytes, 44 chars total ending in =).
If invalid in dev/test, app falls back to per-session temporary key (data lost on restart).
In production, app raises RuntimeError — fails hard by design.
See core/security/encryption.py _init_fernet().

## ENABLE_WEB_APP
Must be False — the web_app router has broken imports not worth fixing.

## Alembic
DB schema already migrated. Run `alembic stamp head` if migrations show "already exists" errors (schema pre-existed from prior session).
