# ============================
# WOLLOYEWA STORE BOT - ROLE CHECK MIDDLEWARE
# ============================
"""Role-based access control middleware for bot commands."""

from typing import Callable, Awaitable, List, Optional
from functools import wraps
from telegram import Update
from telegram.ext import ContextTypes

from core.logger import logger
from core.config import settings


class RoleCheckMiddleware:
    """
    Role-based access control middleware.
    
    Restricts access to commands based on user role.
    """
    
    # Role hierarchy (higher number = more permissions)
    ROLE_LEVELS = {
        "customer": 0,
        "vendor": 1,
        "admin": 2,
        "super_admin": 3,
    }
    
    # Required roles for specific commands
    COMMAND_ROLES = {
        "/admin": ["admin", "super_admin"],
        "/stats": ["admin", "super_admin"],
        "/broadcast": ["admin", "super_admin"],
        "/my_products": ["vendor", "admin", "super_admin"],
        "/add_product": ["vendor", "admin", "super_admin"],
        "/vendor_panel": ["vendor", "admin", "super_admin"],
    }
    
    def __init__(self):
        self._admin_ids = set(settings.admin_ids_list)
    
    async def __call__(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
        next_handler: Callable[[Update, ContextTypes.DEFAULT_TYPE], Awaitable[None]],
    ) -> None:
        """
        Process the update with role check.
        
        Args:
            update: Telegram update
            context: Callback context
            next_handler: Next handler in chain
        """
        user_id = update.effective_user.id if update.effective_user else None
        
        if not user_id:
            await next_handler(update, context)
            return
        
        # Extract command
        command = None
        if update.message and update.message.text and update.message.text.startswith('/'):
            command = update.message.text.split()[0]
        
        # Check if command requires specific role
        if command and command in self.COMMAND_ROLES:
            required_roles = self.COMMAND_ROLES[command]
            user_role = context.user_data.get("user_role", "customer")
            
            # Check if user is in admin list
            if user_id in self._admin_ids:
                user_role = "super_admin"
            
            if not self._has_role(user_role, required_roles):
                await update.message.reply_text(
                    "❌ ይህን ትዕዛዝ ለመጠቀም ፈቃድ የለዎትም።\n\n"
                    "ይህ ትዕዛዝ ለአስተዳዳሪዎች ብቻ ነው።"
                )
                logger.warning(f"User {user_id} attempted to use {command} without permission")
                return
        
        # Process the update
        await next_handler(update, context)
    
    def _has_role(self, user_role: str, required_roles: List[str]) -> bool:
        """
        Check if user has required role.
        
        Args:
            user_role: User's role
            required_roles: List of allowed roles
            
        Returns:
            True if user has required role
        """
        user_level = self.ROLE_LEVELS.get(user_role, 0)
        
        for role in required_roles:
            required_level = self.ROLE_LEVELS.get(role, 0)
            if user_level >= required_level:
                return True
        
        return False


# Global role check middleware instance
role_check_middleware = RoleCheckMiddleware()


def admin_only(func):
    """
    Decorator to restrict command to admins only.
    
    Usage:
        @admin_only
        async def admin_command(update, context):
            ...
    """
    @wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        user_id = update.effective_user.id if update.effective_user else None
        
        if user_id not in settings.admin_ids_list:
            await update.message.reply_text(
                "❌ ይህን ትዕዛዝ ለመጠቀም ፈቃድ የለዎትም።\n\n"
                "ይህ ትዕዛዝ ለአስተዳዳሪዎች ብቻ ነው።"
            )
            return
        
        return await func(update, context, *args, **kwargs)
    
    return wrapper


def vendor_only(func):
    """
    Decorator to restrict command to vendors and admins.
    
    Usage:
        @vendor_only
        async def vendor_command(update, context):
            ...
    """
    @wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        user_id = update.effective_user.id if update.effective_user else None
        user_role = context.user_data.get("user_role", "customer")
        
        if user_role not in ["vendor", "admin", "super_admin"] and user_id not in settings.admin_ids_list:
            await update.message.reply_text(
                "❌ ይህን ትዕዛዝ ለመጠቀም ፈቃድ የለዎትም።\n\n"
                "ይህ ትዕዛዝ ለሻጮች እና አስተዳዳሪዎች ብቻ ነው።"
            )
            return
        
        return await func(update, context, *args, **kwargs)
    
    return wrapper


__all__ = ["RoleCheckMiddleware", "role_check_middleware", "admin_only", "vendor_only"]