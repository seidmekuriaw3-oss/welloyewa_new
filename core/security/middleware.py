<<<<<<< HEAD
=======
"""Security headers middleware for FastAPI."""

>>>>>>> 58a16d4ee3078d96a16a22860de294107e7c3aef
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
<<<<<<< HEAD
=======
    """Middleware to add security headers to all responses."""

>>>>>>> 58a16d4ee3078d96a16a22860de294107e7c3aef
    async def dispatch(self, request: Request, call_next) -> Response:
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "SAMEORIGIN"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
<<<<<<< HEAD
        return response


__all__ = ["SecurityHeadersMiddleware"]
=======
        response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
        return response
>>>>>>> 58a16d4ee3078d96a16a22860de294107e7c3aef
