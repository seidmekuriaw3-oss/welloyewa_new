# Security hardening and deployment checklist

This document records concrete safeguards and remaining operational risks. It is
not a third-party audit, a compliance certification, or a numerical security
score.

## Safeguards implemented

- Production configuration rejects missing or placeholder credentials, invalid
  Fernet encryption keys, wildcard host/CORS allowlists, debug mode, disabled
  rate limiting, and development-only behavior.
- Production startup stops when PostgreSQL or Redis cannot initialize. Redis
  backs the shared API minute/hour limits; local development may continue with
  its in-process limiter.
- Host headers are checked against `ALLOWED_HOSTS`; CORS response headers are
  explicitly constrained.
- Generic server failures and production health responses avoid returning
  exception text, connection details, or per-service diagnostics.
- Payment initiation and verification are tied to the authenticated user's
  order, stored transaction, configured provider, expected amount, and ETB
  currency. Successful initiation stores the transaction reference.
- Telegram webhook routes validate Telegram's secret-token header. Payment
  gateway webhooks validate provider signatures before scheduling updates.
- Vendor order responses include only line items assigned to that vendor.
- Product search and admin user listing apply filters before pagination and
  return the filtered total.
- Refund validation uses the remaining refundable balance and supports partial
  refunds. The order is marked refunded only when the cumulative refund reaches
  its total.
- Docker Compose requires configured credentials and binds database, Redis,
  metrics, and administration ports to loopback. Only the configured reverse
  proxy is intended to expose public HTTP(S).

## Operator actions required before production

1. Copy `.env.example` to `.env` and replace every `CHANGE_ME` value with
   unique, strong credentials. Use valid JSON arrays for
   `CORS_ALLOWED_ORIGINS` and `ALLOWED_HOSTS`.
2. Confirm the public application domain is present in both the CORS origin and
   host allowlists. Keep `DEBUG=False` and all `DEV_*` options disabled.
3. Apply database migrations before starting the production application.
4. Terminate TLS at the reverse proxy and keep internal service ports private.
5. Review backup encryption, retention, and restore procedures for the chosen
   production storage.
6. Run the project test suite and a deployment smoke test before publishing.

## Key and repository-history risk

The development encryption key file is tracked in Git. Its contents have not
been inspected, removed, rotated, or purged from repository history. This
requires an explicit operator decision because rotating it can make existing
encrypted development data unreadable, while rewriting history affects every
existing clone. Do not treat the ignore rule as removing an already tracked
file; resolve this risk through a coordinated key/history plan.

## Verification record

Update this section only with checks that were actually run against the current
workspace. Passing local checks do not replace provider, deployment, or
operational review.
