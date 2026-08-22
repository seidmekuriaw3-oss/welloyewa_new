# ============================
# WOLLOYEWA STORE BOT - MIDDLEWARES MODULE
# ============================
"""Telegram bot middleware for request processing and logging."""

from bot.middlewares.analytics_mw import AnalyticsMiddleware, analytics_middleware
from bot.middlewares.auth import AuthMiddleware, auth_middleware
from bot.middlewares.i18n import I18nMiddleware, get_user_language, i18n_middleware
from bot.middlewares.logging import LoggingMiddleware, logging_middleware
from bot.middlewares.role_check import RoleCheckMiddleware, admin_only, role_check_middleware
from bot.middlewares.throttling import ThrottlingMiddleware, throttling_middleware

__all__ = [
    # Analytics
    "AnalyticsMiddleware",
    # Auth
    "AuthMiddleware",
    # I18n
    "I18nMiddleware",
    # Logging
    "LoggingMiddleware",
    # Role Check
    "RoleCheckMiddleware",
    # Throttling
    "ThrottlingMiddleware",
    "admin_only",
    "analytics_middleware",
    "auth_middleware",
    "get_user_language",
    "i18n_middleware",
    "logging_middleware",
    "role_check_middleware",
    "throttling_middleware",
]
