# ============================
# WOLLOYEWA STORE BOT - I18N MIDDLEWARE
# ============================
"""Internationalization middleware for multi-language support."""

from typing import Callable, Awaitable, Dict, Any
from telegram import Update
from telegram.ext import ContextTypes

from core.logger import logger
from apps.users.services import UserService
from infrastructure.database.session import get_db_session


class I18nMiddleware:
    """
    Internationalization middleware for bot messages.
    
    Supports:
    - Amharic (am)
    - English (en)
    - Oromo (om)
    """
    
    # Translation strings
    TRANSLATIONS = {
        "am": {
            "welcome": "እንኳን ደህና መጡ!",
            "error": "ስህተት ተከስቷል። እባክዎ ቆይተው እንደገና ይሞክሩ።",
            "not_found": "አልተገኘም።",
            "success": "ተሳክቷል!",
            "cancel": "ተሰርዟል።",
            "confirm": "አረጋግጥ",
            "back": "ወደ ኋላ",
            "next": "ቀጣይ",
            "save": "አስቀምጥ",
            "delete": "ሰርዝ",
            "edit": "አርትዕ",
            "search": "ፈልግ",
            "cart": "ቅርጫት",
            "checkout": "ግዢ አጠናቅቅ",
            "profile": "ፕሮፋይል",
            "orders": "ትዕዛዞች",
            "wishlist": "ተመራጮች",
        },
        "en": {
            "welcome": "Welcome!",
            "error": "An error occurred. Please try again later.",
            "not_found": "Not found.",
            "success": "Success!",
            "cancel": "Cancelled.",
            "confirm": "Confirm",
            "back": "Back",
            "next": "Next",
            "save": "Save",
            "delete": "Delete",
            "edit": "Edit",
            "search": "Search",
            "cart": "Cart",
            "checkout": "Checkout",
            "profile": "Profile",
            "orders": "Orders",
            "wishlist": "Wishlist",
        },
        "om": {
            "welcome": "Baga nagaan dhufte!",
            "error": "Dogoggorri uumame. Mee booda deebi'ii yaali.",
            "not_found": "Hin argamne.",
            "success": "Milkaa'e!",
            "cancel": "Haquf.",
            "confirm": "Mirkaneessi",
            "back": "Duuba",
            "next": "Itti aansaa",
            "save": "Kuusi",
            "delete": "Haqi",
            "edit": "Gulaali",
            "search": "Barbaadi",
            "cart": "Gaatarii",
            "checkout": "Bittaa xumuri",
            "profile": "Buufata",
            "orders": "Ajajawwan",
            "wishlist": "Bassawwan",
        },
    }
    
    def __init__(self):
        self._user_languages: Dict[int, str] = {}
        self._default_language = "am"
    
    async def __call__(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
        next_handler: Callable[[Update, ContextTypes.DEFAULT_TYPE], Awaitable[None]],
    ) -> None:
        """
        Process the update with language support.
        
        Args:
            update: Telegram update
            context: Callback context
            next_handler: Next handler in chain
        """
        user_id = update.effective_user.id if update.effective_user else None
        
        # Get user's language preference
        if user_id:
            language = await self.get_user_language(user_id)
            context.user_data["language"] = language
        
        # Store translation function in context
        context.user_data["t"] = self.get_translator(context.user_data.get("language", self._default_language))
        
        await next_handler(update, context)
    
    async def get_user_language(self, user_id: int) -> str:
        """
        Get user's preferred language.
        
        Args:
            user_id: User ID
            
        Returns:
            Language code (am, en, om)
        """
        # Check cache
        if user_id in self._user_languages:
            return self._user_languages[user_id]
        
        # Get from database
        async for db in get_db_session():
            user_service = UserService(db)
            user = await user_service.get_user_by_telegram(user_id)
            
            if user and user.language:
                language = user.language
            else:
                language = self._default_language
            
            self._user_languages[user_id] = language
            return language
        
        return self._default_language
    
    def get_translator(self, language: str) -> callable:
        """
        Get translation function for a language.
        
        Args:
            language: Language code
            
        Returns:
            Translation function
        """
        translations = self.TRANSLATIONS.get(language, self.TRANSLATIONS[self._default_language])
        
        def translate(key: str, **kwargs) -> str:
            """Translate a key with optional formatting."""
            text = translations.get(key, key)
            if kwargs:
                return text.format(**kwargs)
            return text
        
        return translate
    
    async def set_user_language(self, user_id: int, language: str) -> None:
        """
        Set user's preferred language.
        
        Args:
            user_id: User ID
            language: Language code
        """
        if language not in self.TRANSLATIONS:
            language = self._default_language
        
        # Update cache
        self._user_languages[user_id] = language
        
        # Update database
        async for db in get_db_session():
            user_service = UserService(db)
            user = await user_service.get_user_by_telegram(user_id)
            
            if user:
                await user_service.update_user(user.id, {"language": language})
            break


# Global i18n middleware instance
i18n_middleware = I18nMiddleware()


def get_user_language(context: ContextTypes.DEFAULT_TYPE) -> str:
    """Get current user's language from context."""
    return context.user_data.get("language", "am")


def get_translator(context: ContextTypes.DEFAULT_TYPE) -> callable:
    """Get translation function from context."""
    return context.user_data.get("t", lambda x: x)


__all__ = ["I18nMiddleware", "i18n_middleware", "get_user_language", "get_translator"]