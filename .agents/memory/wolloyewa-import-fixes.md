---
name: Wolloyewa Store Bot import fixes
description: Patterns of import errors found and fixed during initial setup of the Wolloyewa Telegram bot project
---

## Common patterns fixed

**Pydantic DSN objects must be cast to str:**
- `str(settings.DATABASE_URL)` before passing to SQLAlchemy
- `str(settings.REDIS_URL)` before passing to redis.from_url()
- Pydantic v2 `PostgresDsn` / `RedisDsn` are not plain strings

**asyncpg sslmode:** Strip `?sslmode=disable` from DATABASE_URL before passing to asyncpg engine; asyncpg does not accept it as a URL param.

**SQLAlchemy reserved attribute:** Column named `metadata` clashes with SQLAlchemy Declarative API — renamed to `extra_data`.

**Missing function aliases:** Many modules expected aliases that didn't exist:
- `paginate` → alias for `paginate_query` in pagination.py
- `parse_date` → alias for `DateHelper.parse_date` in date_helpers.py
- `compress_image` → module-level function wrapping `MediaOptimizer.compress_image`
- `verify_telegram_webhook` → added to core/security/__init__.py
- `AsyncSessionLocal` → `_session_manager._sessionmaker` alias in session.py
- `SearchService` → class wrapping `ProductService.search_products` in products/services.py
- `MarketingService` → composite class in apps/marketing/__init__.py
- `LoyaltyRepository` → alias for `LoyaltyTransactionRepository`
- Router aliases: `health_router`, `webhook_router`, etc. added to infrastructure/api/v1/__init__.py

**Missing modules created:**
- `apps/payments/` (schemas only, no models needed)
- `infrastructure/monitoring/` (stubs forwarding to core/monitoring/)

**Wrong import paths:**
- `from core.redis.client` → `from infrastructure.redis.client`
- `from core.database` → `from infrastructure.database.session`

**Pydantic v2 root_validator:** Must use `@root_validator(skip_on_failure=True)` not bare `@root_validator`

**python-telegram-bot v20+ PicklePersistence:** `store_bot_data`, `store_user_data`, `store_chat_data` kwargs removed — use default constructor.

**Missing packages:** `reportlab`, `psutil` — installed via pip.
