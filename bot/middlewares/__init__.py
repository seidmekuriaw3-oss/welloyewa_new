# ============================
# WOLLOYEWA STORE BOT - MIDDLEWARES MODULE
# ============================
"""Telegram bot middleware for request processing and logging."""

from bot.middlewares.auth import AuthMiddleware, auth_middleware
from bot.middlewares.analytics_mw import AnalyticsMiddleware, analytics_middleware
from bot.middlewares.throttling import ThrottlingMiddleware, throttling_middleware
from bot.middlewares.i18n import I18nMiddleware, i18n_middleware, get_user_language
from bot.middlewares.logging import LoggingMiddleware, logging_middleware
from bot.middlewares.role_check import RoleCheckMiddleware, role_check_middleware, admin_only

__all__ = [
    # Auth
    "AuthMiddleware",
    "auth_middleware",
    # Analytics
    "AnalyticsMiddleware",
    "analytics_middleware",
    # Throttling
    "ThrottlingMiddleware",
    "throttling_middleware",
    # I18n
    "I18nMiddleware",
    "i18n_middleware",
    "get_user_language",
    # Logging
    "LoggingMiddleware",
    "logging_middleware",
    # Role Check
    "RoleCheckMiddleware",
    "role_check_middleware",
    "admin_only",
]