# ============================
# WOLLOYEWA STORE BOT - LOCATION HANDLER
# ============================
"""Telegram bot location sharing handlers."""

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from core.logger import logger
from apps.users.services import UserService
from infrastructure.database.session import get_db_session


async def location_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle the /location command.
    
    Asks user to share their location.
    """
    keyboard = [
        [
            InlineKeyboardButton("📍 ቦታዬን አጋራ", callback_data="share_location"),
            InlineKeyboardButton("🏙️ ከተማ አስገባ", callback_data="enter_city"),
        ],
        [InlineKeyboardButton("🔙 ወደ ኋላ", callback_data="menu_back")],
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "📍 *ቦታ ማጋራት*\n\n"
        "የአቅራቢያ ምርቶችን ለማየት እና የማድረስ አማራጮችን ለማግኘት እባክዎ ቦታዎን ያጋሩ።\n\n"
        "ወይም ከተማዎን በመጻፍ ማስገባት ይችላሉ።",
        parse_mode="Markdown",
        reply_markup=reply_markup
    )


async def location_message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle location message.
    
    Saves user's location to database.
    """
    location = update.message.location
    user_id = update.effective_user.id
    
    async for db in get_db_session():
        user_service = UserService(db)
        user = await user_service.get_user_by_telegram(user_id)
        
        if user:
            await user_service.update_user(user.id, {
                "location_lat": location.latitude,
                "location_lng": location.longitude,
            })
            
            # Try to get city from coordinates (reverse geocoding)
            city = await reverse_geocode(location.latitude, location.longitude)
            if city:
                await user_service.update_user(user.id, {"city": city})
        break
    
    await update.message.reply_text(
        "✅ *ቦታዎ ተመዝግቧል!*\n\n"
        "በአካባቢዎ ያሉ ምርቶችን ለማየት /menu ይጫኑ።",
        parse_mode="Markdown"
    )


async def location_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle location-related callbacks.
    """
    query = update.callback_query
    await query.answer()
    
    if query.data == "share_location":
        # Request location
        keyboard = [
            [InlineKeyboardButton("📍 ቦታዬን አጋራ", callback_data="share_location")],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.message.reply_text(
            "📍 እባክዎ ከታች ያለውን ቁልፍ በመጫን ቦታዎን ያጋሩ።",
            reply_markup=reply_markup
        )
        
        # Force reply location button
        await query.message.reply_location(
            request_location=True
        )
        
    elif query.data == "enter_city":
        await query.message.edit_text(
            "🏙️ *ከተማ ያስገቡ*\n\n"
            "እባክዎ የሚኖሩበትን ከተማ ይጻፉ።\n\n"
            "ለምሳሌ: አዲስ አበባ, ድሬ ዳዋ, ባህር ዳር",
            parse_mode="Markdown"
        )
        context.user_data["awaiting_city"] = True


async def city_text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle city text input.
    """
    if context.user_data.get("awaiting_city"):
        city = update.message.text.strip()
        user_id = update.effective_user.id
        
        async for db in get_db_session():
            user_service = UserService(db)
            user = await user_service.get_user_by_telegram(user_id)
            
            if user:
                await user_service.update_user(user.id, {"city": city})
            break
        
        context.user_data["awaiting_city"] = False
        
        await update.message.reply_text(
            f"✅ *ከተማዎ {city} ተመዝግቧል!*\n\n"
            f"በከተማዎ ያሉ ምርቶችን ለማየት /menu ይጫኑ።",
            parse_mode="Markdown"
        )


async def reverse_geocode(latitude: float, longitude: float) -> str:
    """
    Reverse geocode coordinates to city name.
    
    Args:
        latitude: Latitude coordinate
        longitude: Longitude coordinate
        
    Returns:
        City name or None
    """
    # In production, use a geocoding API
    # For now, return default city
    return "Addis Ababa"


__all__ = [
    "location_command",
    "location_message_handler",
    "location_callback",
    "city_text_handler",
]