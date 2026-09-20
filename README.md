# Wolloyewa Store Bot

[![Python](https://img.shields.io/badge/Python-3.11-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.108%2B-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![Telegram](https://img.shields.io/badge/Telegram-Bot-26A5E4?logo=telegram&logoColor=white)](https://core.telegram.org/bots)
[![License](https://img.shields.io/badge/License-Proprietary-red.svg)](LICENSE)

Wolloyewa is an Ethiopian multi-vendor commerce platform built around a Telegram bot, a Telegram Mini App, and a FastAPI backend. It provides product browsing, search, carts, orders, vendor management, administration, inventory, reviews, notifications, and Ethiopian payment integrations.

The interface supports Amharic, English, and Afaan Oromoo where translations are available.

## Contents

- [Features](#features)
- [Architecture](#architecture)
- [Requirements](#requirements)
- [Local setup](#local-setup)
- [Configuration](#configuration)
- [Run](#run)
- [Database](#database)
- [Telegram bot](#telegram-bot)
- [Web app and API](#web-app-and-api)
- [Testing](#testing)
- [Deployment](#deployment)
- [Security](#security)
- [Troubleshooting](#troubleshooting)
- [Project layout](#project-layout)

## Features

### Customers

- Browse active products by category and search by name.
- View prices, stock, images, ratings, descriptions, and vendor details.
- Manage a cart, delivery addresses, wishlist, and order history.
- Create orders using Chapa, Telebirr, CBE Birr, or cash on delivery when configured.
- Receive Telegram order confirmations and submit product reviews.

### Vendors and administrators

- Vendor registration and vendor-scoped product CRUD.
- Inventory quantities, thresholds, stock alerts, and order workflows.
- Sales dashboards, reports, audit logs, broadcasts, and user/vendor administration.

### Platform

- Async FastAPI, SQLAlchemy 2, and PostgreSQL.
- Alembic migrations and Redis-backed Telegram persistence.
- JWT authentication, Telegram `initData` verification, rate limiting, security headers, PII masking, and audit logging.
- Payment webhook signature verification for configured providers.
- Docker, scheduled tasks, backups, monitoring, and CI security-scan configuration.

## Architecture

```text
Telegram user -> python-telegram-bot handlers -> services -> repositories -> PostgreSQL
									  |
									  +-> Redis persistence

Browser / Telegram Mini App -> FastAPI web routes and REST API -> same services/database
Payment providers -> signed webhook endpoints -> payment verification -> order updates
```

## Requirements

- Python 3.11
- PostgreSQL 14+
- Redis 6+ for persistent bot conversations (optional locally)
- Telegram bot token from [@BotFather](https://t.me/BotFather)
- Public HTTPS for a Telegram Mini App and production webhooks

Runtime versions are defined in `requirements.txt` and `pyproject.toml`. Always use the project virtual environment.

## Local setup

### Windows PowerShell

```powershell
py -3.11 -m venv .venv311
Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned
.\.venv311\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

For development tools:

```powershell
pip install -r requirements-dev.txt
```

### Linux or macOS

```bash
python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
```

Create `.env` from the required settings below. Never commit `.env` or share its values in logs, screenshots, issues, or chat.

## Configuration

| Variable | Purpose | Local value |
| --- | --- | --- |
| `ENVIRONMENT` | Runtime mode | `development` |
| `DEBUG` | Development diagnostics | `True` locally, `False` in production |
| `HOST` / `PORT` | HTTP bind address and port | `0.0.0.0` / `8080` |
| `DATABASE_URL` | PostgreSQL connection | Secret-managed value |
| `REDIS_URL` | Redis connection | `redis://localhost:6379/0` |
| `TELEGRAM_BOT_TOKEN` | Telegram API token | Secret-managed value |
| `WEB_APP_URL` | Mini App URL | `https://.../app/` for Telegram |
| `TELEGRAM_WEBHOOK_URL` | Webhook base URL | Public HTTPS only |
| `CHAPA_SECRET_KEY` | Chapa API credential | Secret-managed value |
| `CHAPA_WEBHOOK_SECRET` | Chapa signing secret | Secret-managed value |
| `TELEBIRR_APP_KEY` | Telebirr credential | Secret-managed value |
| `CBE_BIRR_SECRET_KEY` | CBE Birr signing secret | Secret-managed value |
| `JWT_SECRET_KEY` | JWT signing key | Strong random secret |
| `ENCRYPTION_KEY` | Fernet encryption key | Valid Fernet key |
| `ADMIN_IDS` | Telegram admin IDs | Comma-separated IDs |

Production must use `ENVIRONMENT=production`, `DEBUG=False`, unique secrets, a permanent HTTPS domain, restricted CORS/hosts, real payment credentials, and a secret manager.

Generate a Fernet key with:

```powershell
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

## Run

Start the API, web app, and local Telegram polling process:

```powershell
python main.py
```

Open locally at:

```text
http://127.0.0.1:8080/app/
```

`0.0.0.0` is a server bind address, not a browser destination. For phone testing and Telegram Mini Apps, expose port 8080 with a public HTTPS tunnel:

```powershell
cloudflared tunnel --protocol http2 --url http://localhost:8080
$env:WEB_APP_URL="https://your-name.trycloudflare.com/app/"
python main.py
```

Keep both processes running. Quick Tunnel URLs are temporary and must not be used for production.

## Database

```powershell
alembic upgrade head
$env:PYTHONPATH=(Get-Location).Path
python scripts/seed_db.py
```

The seed script is for development only. It creates sample categories, vendor data, products, customers, and orders. Do not run it against production. Back up production before migrations.

## Telegram bot

Use exactly one update mode per bot: polling for a controlled worker or webhooks for a public deployment. Do not run both at once.

Useful commands:

```text
/start       Start the bot
/menu        Browse categories and products in Telegram
/search      Search products
/cart        View the cart
/checkout    Start checkout
/profile     View profile
/orders      View orders
/wishlist    View saved products
/shop        Open the Mini App
/help        Show help
```

## Web app and API

Web pages are served under `/app/`:

```text
/app/                 Home
/app/categories       Categories
/app/login            Login
/app/register         Registration
/app/cart             Cart
/app/checkout         Checkout
/app/orders           Orders
/app/dashboard        Profile/dashboard
/app/product/{id}     Product detail
```

Mini App API endpoints include:

```text
GET /app/api/categories
GET /app/api/products?page=1&page_size=20
GET /app/api/products?q=phone
GET /app/api/products?category_id=1
GET /app/api/product/{id}
POST /app/api/checkout
POST /app/api/auth
POST /app/api/my-orders
```

The versioned REST API is under `/api/v1`. Main groups are `/users`, `/products`, `/orders`, `/payments`, `/analytics`, `/dashboards`, `/admin`, and `/webhooks`. Interactive documentation is available outside production at `/api/docs` and `/api/redoc`.

## Testing

```powershell
python -m pytest
python -m pytest tests/test_unit/test_security.py -o addopts=""
python -m pytest tests/test_api/test_products.py -o addopts=""
python -m compileall -q .
python -m pip check
ruff check .
```

API tests require the isolated test PostgreSQL database configured in `tests/conftest.py`. Never point tests at development or production data.

## Deployment

```bash
docker compose up -d --build
```

The container entrypoint waits for dependencies and runs migrations before starting the selected service. Verify `docker-compose.yml` and all production environment values first.

Before release:

1. Rotate credentials exposed in logs, screenshots, `.env` files, or chat.
2. Set production mode and disable debug fallbacks.
3. Configure permanent HTTPS, TLS termination, firewall rules, restricted CORS, and allowed hosts.
4. Configure PostgreSQL, Redis, backups, monitoring, and one Telegram update consumer.
5. Configure payment callbacks and verify provider-specific signatures with official documentation.
6. Test health, readiness, authentication, catalog, checkout, payments, and graceful shutdown.

Health endpoints: `/health`, `/ready`, and `/live`.

## Security

- Keep secrets outside source control and rotate compromised credentials immediately.
- Never use DEBUG authentication or checkout fallbacks in production.
- Require HTTPS for Mini Apps and webhook endpoints.
- Validate Telegram `initData` freshness and payment webhook signatures.
- Use least-privilege database and Redis credentials.
- Review audit logs and failed authentication events.
- Run dependency, secret, container, and static security scans before release.

See `docs/security_audit.md` for the operational security checklist.

## Troubleshooting

**Browser shows `ERR_ADDRESS_INVALID`:** use `http://127.0.0.1:8080/app/`, not `0.0.0.0`.

**Telegram does not respond:** confirm `Telegram bot polling started!` in logs, verify the token, ensure no second polling process is running, and check that `DISABLE_BOT_POLLING` is not enabled locally.

**Telegram says the Web App URL is invalid:** `WEB_APP_URL` must be a reachable HTTPS URL. Restart the application after changing it.

**Cloudflare returns 1033 or 502:** the tunnel stopped, its temporary URL changed, or the local app is not listening on port 8080. Restart both processes and update `WEB_APP_URL`.

**Categories show but products are empty:** check `GET /app/api/products`, seed the development database, and restart the application so its database pool reloads the data.

## Project layout

```text
alembic/                 Database migrations
apps/                    Domain models, repositories, schemas, and services
bot/                     Telegram bot, web app, templates, and static files
core/                    Configuration, security, logging, events, and utilities
devops/                  CI/CD, monitoring, Kubernetes, and infrastructure config
docs/                    Architecture, deployment, compliance, and user documentation
infrastructure/          API, database, payments, queues, storage, and workers
scripts/                 Seed, migration, backup, and operational scripts
tests/                   Unit, API, service, integration, and bot tests
main.py                  FastAPI application and lifecycle entry point
```

## License

This project is proprietary. See [LICENSE](LICENSE) for the applicable terms.
