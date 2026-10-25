# ============================
# WOLLOYEWA STORE BOT - LOCATION HANDLER
# ============================
"""Telegram bot location sharing handlers."""

from telegram import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
    Update,
)
from telegram.ext import ContextTypes

from apps.users.schemas import UserUpdate
from apps.users.services import UserService
from bot.handlers.callback_utils import answer_callback_query
from bot.handlers.text_routing import mark_text_message_handled
from bot.localization import tr
from infrastructure.database.session import transaction_session


async def location_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle the /location command.

    Asks user to share their location.
    """
    keyboard = [
        [
            InlineKeyboardButton(tr(context, "location_share"), callback_data="share_location"),
            InlineKeyboardButton(tr(context, "location_enter_city"), callback_data="enter_city"),
        ],
        [InlineKeyboardButton(tr(context, "back"), callback_data="menu_back")],
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        f"{tr(context, 'location_title')}\n\n{tr(context, 'location_prompt')}",
        parse_mode="Markdown",
        reply_markup=reply_markup,
    )


async def location_message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle location message.

    Saves user's location to database.
    """
    if context.user_data.get("awaiting_city"):
        return
    if context.user_data.get("checkout_in_progress"):
        if context.user_data.get("checkout_conversation_active"):
            return
        context.user_data.pop("checkout_in_progress", None)
        await update.message.reply_text(
            tr(context, "checkout_session_expired"),
            reply_markup=ReplyKeyboardRemove(),
        )
        return

    location = update.message.location
    user_id = update.effective_user.id

    saved = False
    async with transaction_session() as db:
        user_service = UserService(db)
        user = await user_service.get_user_by_telegram(user_id)

        if user:
            await user_service.update_user(
                user.id,
                UserUpdate(
                    location_lat=location.latitude,
                    location_lng=location.longitude,
                ),
            )

            # Try to get city from coordinates (reverse geocoding)
            city = await reverse_geocode(location.latitude, location.longitude)
            if city:
                await user_service.update_user(user.id, UserUpdate(city=city))
            saved = True

    await update.message.reply_text(
        tr(context, "location_saved" if saved else "location_failed"),
        parse_mode="Markdown",
        reply_markup=ReplyKeyboardRemove(),
    )


async def location_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle location-related callbacks.
    """
    query = update.callback_query
    if not await answer_callback_query(query):
        return

    if query.data == "share_location":
        # Telegram only supports request_location on a ReplyKeyboard button,
        # not on InlineKeyboardButton or reply_location().
        reply_markup = ReplyKeyboardMarkup(
            [[KeyboardButton(tr(context, "location_share"), request_location=True)]],
            one_time_keyboard=True,
            resize_keyboard=True,
        )
        await query.message.reply_text(
            tr(context, "location_share_prompt"), reply_markup=reply_markup
        )

    elif query.data == "enter_city":
        await query.message.edit_text(
            tr(context, "location_city_prompt"),
            parse_mode="Markdown",
        )
        context.user_data["awaiting_city"] = True


async def city_text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle city text input.
    """
    if context.user_data.get("awaiting_city"):
        mark_text_message_handled(update, context)
        city = update.message.text.strip()
        user_id = update.effective_user.id

        async with transaction_session() as db:
            user_service = UserService(db)
            user = await user_service.get_user_by_telegram(user_id)

            if user:
                await user_service.update_user(user.id, UserUpdate(city=city))
                saved = True
            else:
                saved = False

        context.user_data["awaiting_city"] = False

        await update.message.reply_text(
            tr(
                context,
                "location_city_saved" if saved else "location_failed",
                city=city,
            ),
            parse_mode="Markdown",
            reply_markup=ReplyKeyboardRemove(),
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
    "city_text_handler",
    "location_callback",
    "location_command",
    "location_message_handler",
]
