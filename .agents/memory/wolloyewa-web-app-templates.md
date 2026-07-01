---
name: Wolloyewa web app templates
description: Patterns, security rules, and routing for the Telegram Mini App HTML templates at bot/web_app/templates/
---

## Template structure
8 Jinja2 templates: base.html, index.html, categories.html, product.html, cart.html, checkout.html, orders.html, dashboard.html. All extend base.html via `{% extends "base.html" %}`.

## API routing rule
Mini-app pages MUST use `/app/api/*` (web_app_router), NOT `/api/v1/*` directly.
- Products list: `GET /app/api/products`
- Categories: `GET /app/api/categories` (proxied in web_app router to CategoryService)
- Single product: `GET /app/api/product/{id}`
- Checkout: `POST /app/api/checkout`
- Auth: `POST /app/api/auth`
- Orders: `POST /app/api/my-orders`

**Why:** Keeps mini-app isolated from backend API versioning; the web_app router owns its own contract.

## XSS safety rule
All untrusted API/user data rendered into the DOM must use DOM APIs (`.textContent`, `.setAttribute`), NOT `innerHTML` string interpolation. Two helpers in `app.js`:
- `he(str)` — HTML-escapes a string for innerHTML contexts
- `safeUrl(url)` — validates http/https before using in src/href

**Why:** Product names, descriptions, order numbers come from DB (ultimately user-supplied); innerHTML injection is a direct XSS vector.

## Telegram auth freshness
`_verify_telegram_init_data()` in `bot/web_app/router.py` now validates `auth_date` age (max 1 hour = `_INIT_DATA_MAX_AGE_SECONDS = 3600`) before accepting initData.
**Why:** Without this check, a replayed/stolen initData token would be valid indefinitely as long as the HMAC matched.

## Browser 401 on /app/api/my-orders is expected
In browser preview (no Telegram context), auth endpoints return 401. This is correct behavior — they require Telegram `initData` which is only present inside a real Telegram Mini App session.

## Redis fallback
Bot uses JSON file persistence when Redis is unavailable (localhost:6379 refused). Conversation state survives across messages within a session but resets on process restart. Task 4 (add Redis) would fix this.
