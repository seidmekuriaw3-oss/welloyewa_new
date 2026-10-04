# Security baseline and operations checklist

This document describes application safeguards and deployment checks. It is not an independent security audit, a compliance certification, or a guarantee that a deployment is secure.

## Application safeguards

- Production configuration requires explicit application, JWT, encryption, database, Redis, and Telegram webhook secrets.
- Production startup rejects wildcard CORS and Host allowlists. Configure explicit origins and hosts, or set `REPLIT_DOMAINS` / `WEB_APP_URL` for domain-based allowlist defaults.
- `TrustedHostMiddleware` rejects requests whose Host header is not allowed. API documentation routes are disabled in production.
- API route groups use configured per-minute and per-hour rate limits. Redis is used for shared limits when available; local development can use in-memory limits.
- Telegram webhooks verify Telegram's secret-token header. Payment webhooks verify provider signatures before queuing payment updates.
- Payment verification is tied to the customer's stored transaction and order and checks the provider, transaction ID, amount, and currency before marking an order paid.
- Generic application errors return a fixed message. Detailed health-check messages and metadata are withheld in production.
- Compose requires secrets instead of insecure password fallbacks and binds database, Redis, app, and monitoring ports to loopback. Nginx is the only service configured with public HTTP/HTTPS ports.

## Deployment checklist

1. Keep real credentials in Replit Secrets or a production secret manager; never put them in `.env.example`, source control, container images, logs, or screenshots.
2. Use distinct, strong values for `SECRET_KEY`, `JWT_SECRET_KEY`, `ENCRYPTION_KEY`, and `TELEGRAM_WEBHOOK_SECRET`.
3. Set `ENVIRONMENT=production`, `DEBUG=False`, explicit database and Redis URLs, and exact CORS/Host allowlists.
4. Use HTTPS for the Mini App and all public webhooks. Configure each payment provider's signing secret and test valid and invalid signatures.
5. Restrict database and Redis network access. Keep Flower, Prometheus, and Grafana behind loopback, a VPN, or an authenticated reverse proxy.
6. Back up data and encryption keys securely before migrations or key changes. Confirm that a restore can decrypt existing encrypted values before rotating a key.
7. Run the test suite and dependency/security scans before release, then verify authentication, role boundaries, product search, vendor order visibility, checkout, payment verification, refunds, and graceful shutdown.

## Open source-control risk

The development encryption key file is ignored going forward and excluded from Docker build contexts, but it is still tracked in the current Git history. Do not use that key for production. Removing it from the repository or rewriting history requires a decision about preserving encrypted development data and coordinating updates for existing clones.