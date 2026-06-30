"""Security headers middleware for FastAPI."""

import os

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

_IS_DEVELOPMENT = os.getenv("ENVIRONMENT", "development") == "development"


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Middleware to add security headers to all responses.

    X-Frame-Options is intentionally omitted: this app serves a Telegram
    Mini App and runs inside Replit's webview — both of which embed pages
    in iframes from different origins.  SAMEORIGIN would silently block
    both.  Frame security is handled by Telegram's own sandbox instead.
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        if not _IS_DEVELOPMENT:
            response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
        return response


__all__ = ["SecurityHeadersMiddleware"]
