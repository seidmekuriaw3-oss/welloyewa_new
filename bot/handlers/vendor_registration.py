"""Step-by-step Telegram vendor application and admin review notifications."""

import asyncio
from urllib.parse import urlsplit

from pydantic import ValidationError as SchemaValidationError
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.error import TelegramError
from telegram.ext import ContextTypes, ConversationHandler

from apps.users.repository import UserRepository, VendorRepository
from apps.users.schemas import VendorApplicationCreate
from apps.users.services import VendorService
from bot.handlers.callback_utils import answer_callback_query
from bot.handlers.text_routing import mark_text_message_handled
from core.config import settings
from core.logger import logger
from core.utils.validators import Validator, validate_business_license, validate_ethiopian_tin
from infrastructure.database.session import transaction_session

_STATE_KEY = "vendor_application_step"
_DRAFT_KEY = "vendor_application_draft"
_notification_fallback_tasks: set[asyncio.Task[None]] = set()
_SKIP = {"skip", "алгасах", "дар"}
_CATEGORIES = {
    "furniture": "Furniture",
    "тавилга": "Furniture",
    "electronics": "Electronics",
    "ኤሌክትሮኒክስ": "Electronics",
    "clothing": "Clothing",
    "ልብስ": "Clothing",
    "food": "Food & Beverage",
    "food & beverage": "Food & Beverage",
    "ምግብ": "Food & Beverage",
    "beauty": "Beauty & Personal Care",
    "beauty & personal care": "Beauty & Personal Care",
    "ውበት": "Beauty & Personal Care",
    "home": "Home & Kitchen",
    "home & kitchen": "Home & Kitchen",
    "other": "Other",
    "ሌላ": "Other",
}
_CATEGORY_CHOICES = {
    "furniture": "Furniture",
    "electronics": "Electronics",
    "clothing": "Clothing",
    "food": "Food & Beverage",
    "beauty": "Beauty & Personal Care",
    "home": "Home & Kitchen",
    "other": "Other",
}
_BANK_CHOICES = {
    "cbe": "Commercial Bank of Ethiopia",
    "awash": "Awash Bank",
    "abyssinia": "Bank of Abyssinia",
    "dashen": "Dashen Bank",
    "wegagen": "Wegagen Bank",
    "hibret": "Hibret Bank",
    "cooperative": "Cooperative Bank of Oromia",
    "zemen": "Zemen Bank",
}
_STEPS = (
    ("business_name", "Business / store name", 2, 200),
    ("business_license", "Business license number", 6, 20),
    ("license_document", "License photo or PDF", 0, 0),
    ("tin_number", "10-digit TIN", 10, 10),
    ("business_category", "Business category", 2, 100),
    ("region", "Region", 2, 100),
    ("city", "City / town", 2, 100),
    ("subcity", "Sub-city / woreda", 2, 100),
    ("specific_location", "Specific business location", 3, 300),
    ("maps_link", "Google Maps link (or type SKIP)", 0, 500),
    ("bank_name", "Bank name", 2, 100),
    ("bank_account_name", "Bank account holder name", 2, 200),
    ("bank_account_number", "Bank account number", 6, 34),
    ("business_phone", "Contact phone number", 10, 20),
)
VENDOR_STEP_COUNT = len(_STEPS)
VENDOR_CONFIRM_STATE = VENDOR_STEP_COUNT


def _step_keyboard(step_index: int) -> InlineKeyboardMarkup:
    """Build the step-specific choices with consistent back/cancel controls."""
    keyboard: list[list[InlineKeyboardButton]] = []

    if step_index == 4:
        choices = [
            InlineKeyboardButton(
                label,
                callback_data=f"vendor_choice_category_{choice}",
            )
            for choice, label in _CATEGORY_CHOICES.items()
        ]
        keyboard.extend([choices[index : index + 2] for index in range(0, len(choices), 2)])
    elif step_index == 9:
        keyboard.append([InlineKeyboardButton("⏭ Skip", callback_data="vendor_choice_maps_skip")])
    elif step_index == 10:
        choices = [
            InlineKeyboardButton(
                label,
                callback_data=f"vendor_choice_bank_{choice}",
            )
            for choice, label in _BANK_CHOICES.items()
        ]
        choices.append(
            InlineKeyboardButton(
                "Other (type name)",
                callback_data="vendor_choice_bank_other",
            )
        )
        keyboard.extend([choices[index : index + 2] for index in range(0, len(choices), 2)])

    navigation = []
    if step_index > 0:
        navigation.append(InlineKeyboardButton("⬅️ Back", callback_data="vendor_application_back"))
    navigation.append(InlineKeyboardButton("❌ Cancel", callback_data="vendor_application_cancel"))
    keyboard.append(navigation)
    return InlineKeyboardMarkup(keyboard)


def _prompt(step_index: int) -> str:
    key, label, _, _ = _STEPS[step_index]
    prompts = {
        "business_name": "🏪 Send your business / store name (2-200 characters).\nየንግድ ወይም የሱቅ ስም ይላኩ።",
        "business_license": "📄 Send the business license number (6-20 letters or digits).\nየንግድ ፈቃድ ቁጥር ይላኩ።",
        "license_document": "📎 Upload a clear license photo or a PDF document (up to 10 MB).\nየፈቃዱን ግልጽ ፎቶ ወይም PDF ይላኩ።",
        "tin_number": "🧾 Send the 10-digit TIN.\nየግብር መለያ ቁጥሩን (10 አሃዝ) ይላኩ።",
        "business_category": "🛍️ Choose a category: Furniture, Electronics, Clothing, Food & Beverage, Beauty & Personal Care, Home & Kitchen, or Other.\nየንግድ ዘርፉን ይምረጡ።",
        "region": "📍 Send the region / state.\nክልል ይላኩ።",
        "city": "🏙️ Send the city or town.\nከተማ ይላኩ።",
        "subcity": "📌 Send the sub-city or woreda.\nክፍለ ከተማ ወይም ወረዳ ይላኩ።",
        "specific_location": "📍 Send the specific location, street, or nearby landmark.\nዝርዝር አድራሻ፣ መንገድ ወይም የአካባቢ መለያ ይላኩ።",
        "maps_link": "🗺️ Send a Google Maps link, or type SKIP if you do not have one.\nየGoogle Maps አገናኝ ይላኩ ወይም ከሌለ  SKIP ይጻፉ።",
        "bank_name": "🏦 Send the bank name for payouts.\nየባንክ ስም ይላኩ።",
        "bank_account_name": "👤 Send the account holder name exactly as registered at the bank.\nበባንክ የተመዘገበውን የአካውንት ባለቤት ስም ይላኩ።",
        "bank_account_number": "🔢 Send the bank account number (6-34 digits; spaces and dashes are okay).\nየባንክ አካውንት ቁጥር ይላኩ።",
        "business_phone": "📞 Send a valid Ethiopian phone number (09…, 07…, or +251…).\nትክክለኛ የኢትዮጵያ ስልክ ቁጥር ይላኩ።",
    }
    return (
        f"Step {step_index + 1}/{len(_STEPS)} · {label}\n\n"
        f"{prompts[key]}\n\nUse the inline choices when shown, or use Back and Cancel to navigate."
    )


def _first_missing_step(draft: dict) -> int | None:
    """Return the earliest application step whose data is absent."""
    for step_index, (key, _, _, _) in enumerate(_STEPS):
        if key == "license_document":
            if not draft.get("license_document_file_id") or not draft.get("license_document_type"):
                return step_index
        else:
            value = draft.get(key)
            if key not in draft or (
                key != "maps_link"
                and (value is None or (isinstance(value, str) and not value.strip()))
            ):
                return step_index
    return None


async def _resume_missing_step(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    draft: dict,
    *,
    edit_message: bool = False,
) -> int | None:
    """Re-prompt the earliest missing field instead of crashing at confirmation."""
    step_index = _first_missing_step(draft)
    if step_index is None:
        return None

    context.user_data[_STATE_KEY] = step_index
    logger.warning(
        "Vendor application draft is missing required data at step %s",
        step_index + 1,
    )
    text = (
        "Some application details are missing. Please provide this item to continue.\n\n"
        + _prompt(step_index)
    )
    if edit_message and update.callback_query:
        await update.callback_query.edit_message_text(
            text,
            reply_markup=_step_keyboard(step_index),
        )
    else:
        await update.effective_message.reply_text(
            text,
            reply_markup=_step_keyboard(step_index),
        )
    return step_index


async def start_application(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Begin or resume a vendor application for the current Telegram account."""
    if update.callback_query and not await answer_callback_query(update.callback_query):
        return ConversationHandler.END

    tg_user = update.effective_user
    async with transaction_session() as db:
        user = await UserRepository(db).get_by_telegram(tg_user.id)
        if not user:
            await update.effective_message.reply_text(
                "Please use /start first to create your customer account."
            )
            return ConversationHandler.END
        existing = await VendorRepository(db).get_by_user_id(user.id)
        if existing and existing.is_approved:
            await update.effective_message.reply_text("✅ Your vendor account is already approved.")
            return ConversationHandler.END
        if (
            existing
            and existing.rejected_at is None
            and VendorService.is_application_complete(existing)
        ):
            await update.effective_message.reply_text(
                "⏳ Your vendor application is already awaiting admin review."
            )
            return ConversationHandler.END

    context.user_data[_DRAFT_KEY] = {}
    context.user_data[_STATE_KEY] = 0
    await update.effective_message.reply_text(
        "✨ Vendor application · Vendor onboarding\n"
        "We'll collect your business, location, document, and payout details one step at a time.\n"
        "Мэдээллийг нэг нэг алхмаар бүртгэнэ. Дуусаагүй үед Cancel товчийг дарна уу.\n\n"  # noqa: RUF001
        + _prompt(0),
        reply_markup=_step_keyboard(0),
    )
    return 0


async def handle_text(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    *,
    step_index: int | None = None,
) -> int:
    """Validate one text response and advance the application."""
    if step_index is None:
        stored_step = context.user_data.get(_STATE_KEY)
        if stored_step == "confirm":
            step_index = VENDOR_CONFIRM_STATE
        elif isinstance(stored_step, int):
            step_index = stored_step
        else:
            return ConversationHandler.END

    mark_text_message_handled(update, context)
    if step_index == VENDOR_CONFIRM_STATE:
        draft = context.user_data.get(_DRAFT_KEY, {})
        missing_step = await _resume_missing_step(update, context, draft)
        if missing_step is not None:
            return missing_step
        await _show_confirmation(update, context)
        return VENDOR_CONFIRM_STATE
    key, label, minimum, maximum = _STEPS[step_index]
    text = (update.effective_message.text or "").strip()
    value = text
    error = None

    if key == "license_document":
        error = "Please upload a photo or PDF file for the license."
    elif key == "maps_link" and text.casefold() in _SKIP:
        value = None
    elif key == "tin_number" and not validate_ethiopian_tin(text):
        error = "TIN must contain exactly 10 digits."
    elif not minimum <= len(text) <= maximum:
        error = f"{label} must be between {minimum} and {maximum} characters."
    elif key == "business_license":
        value = text.upper()
        if not validate_business_license(value):
            error = "License number must contain 6-20 letters or digits."
    elif key == "business_category":
        value = _CATEGORIES.get(text.casefold())
        if not value:
            error = "Choose one of the listed categories, or enter Other."
    elif key == "maps_link":
        parsed = urlsplit(text)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            error = "Enter a complete http(s) Google Maps link, or type SKIP."
    elif key == "bank_account_number":
        value = "".join(text.split()).replace("-", "")
        if not value.isdigit() or not 6 <= len(value) <= 34:
            error = "The account number must contain 6-34 digits."
    elif key == "business_phone":
        try:
            value = Validator.phone(text, normalize=True)
        except ValueError:
            error = "Enter a valid Ethiopian phone number (09…, 07…, or +251…)."

    if error:
        await update.effective_message.reply_text(
            f"❌ {error}\n\n{_prompt(step_index)}",
            reply_markup=_step_keyboard(step_index),
        )
        return step_index

    context.user_data[_DRAFT_KEY][key] = value
    next_step = step_index + 1
    if next_step < len(_STEPS):
        context.user_data[_STATE_KEY] = next_step
        await update.effective_message.reply_text(
            _prompt(next_step),
            reply_markup=_step_keyboard(next_step),
        )
        return next_step

    missing_step = await _resume_missing_step(
        update,
        context,
        context.user_data.get(_DRAFT_KEY, {}),
    )
    if missing_step is not None:
        return missing_step

    await _show_confirmation(update, context)
    return VENDOR_CONFIRM_STATE


async def handle_document(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    *,
    step_index: int = 2,
) -> int:
    """Accept only an image/PDF under the upload size limit during document step."""
    if step_index != 2:
        return step_index

    message = update.effective_message
    document = message.document
    if message.photo:
        photo = message.photo[-1]
        file_size = photo.file_size or 0
        file_id = photo.file_id
        kind = "photo"
    elif document:
        mime_type = (document.mime_type or "").casefold()
        if mime_type not in {"image/jpeg", "image/png", "application/pdf"}:
            await message.reply_text("❌ Upload a JPEG, PNG, or PDF license document.")
            return 2
        file_size = document.file_size or 0
        file_id = document.file_id
        kind = "document"
    else:
        return 2

    if file_size > 10 * 1024 * 1024:
        await message.reply_text("❌ The license file must be 10 MB or smaller.")
        return 2

    context.user_data[_DRAFT_KEY]["license_document_file_id"] = file_id
    context.user_data[_DRAFT_KEY]["license_document_type"] = kind
    context.user_data[_STATE_KEY] = 3
    await message.reply_text(_prompt(3), reply_markup=_step_keyboard(3))
    return 3


async def application_choice_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Save an inline application choice and continue to the following field."""
    query = update.callback_query
    step_index = context.user_data.get(_STATE_KEY)
    if not isinstance(step_index, int) or step_index >= len(_STEPS):
        await answer_callback_query(query, "This application step has expired.", show_alert=True)
        return ConversationHandler.END
    if not await answer_callback_query(query):
        return step_index

    choice = query.data.removeprefix("vendor_choice_")
    if step_index == 4 and choice.startswith("category_"):
        value = _CATEGORY_CHOICES.get(choice.removeprefix("category_"))
        key = "business_category"
    elif step_index == 9 and choice == "maps_skip":
        value = None
        key = "maps_link"
    elif step_index == 10 and choice.startswith("bank_"):
        bank_choice = choice.removeprefix("bank_")
        if bank_choice == "other":
            await query.message.reply_text(
                "🏦 Type the bank name as a message.",
                reply_markup=_step_keyboard(step_index),
            )
            return step_index
        value = _BANK_CHOICES.get(bank_choice)
        key = "bank_name"
    else:
        await query.message.reply_text(
            "That choice is not available at this application step.",
            reply_markup=_step_keyboard(step_index),
        )
        return step_index

    if value is None and key != "maps_link":
        await query.message.reply_text(
            "That choice is no longer available. Please choose again.",
            reply_markup=_step_keyboard(step_index),
        )
        return step_index

    context.user_data[_DRAFT_KEY][key] = value
    next_step = step_index + 1
    context.user_data[_STATE_KEY] = next_step
    if next_step < len(_STEPS):
        await query.message.reply_text(
            _prompt(next_step),
            reply_markup=_step_keyboard(next_step),
        )
        return next_step

    await _show_confirmation(update, context)
    return VENDOR_CONFIRM_STATE


async def application_navigation_callback(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    """Return to the previous vendor-application field."""
    query = update.callback_query
    if not await answer_callback_query(query):
        return ConversationHandler.END

    current_step = context.user_data.get(_STATE_KEY)
    if current_step == "confirm":
        previous_step = VENDOR_STEP_COUNT - 1
    elif isinstance(current_step, int):
        previous_step = current_step - 1
    else:
        await query.message.reply_text("This application step has expired.")
        return ConversationHandler.END

    if previous_step < 0:
        context.user_data.pop(_DRAFT_KEY, None)
        context.user_data.pop(_STATE_KEY, None)
        await query.edit_message_text("Vendor application cancelled.")
        return ConversationHandler.END

    context.user_data[_STATE_KEY] = previous_step
    await query.edit_message_text("↩️ Returning to the previous application step.")
    await query.message.reply_text(
        _prompt(previous_step),
        reply_markup=_step_keyboard(previous_step),
    )
    return previous_step


async def _show_confirmation(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    draft = context.user_data[_DRAFT_KEY]
    masked_account = f"••••{draft['bank_account_number'][-4:]}"
    text = (
        "📋 Review your vendor application\n\n"
        f"🏪 Store: {draft['business_name']}\n"
        f"📄 License: {draft['business_license']} (document attached)\n"
        f"🧾 TIN: {draft['tin_number']}\n"
        f"🛍️ Category: {draft['business_category']}\n"
        f"📍 Address: {draft['region']}, {draft['city']}, {draft['subcity']}, "
        f"{draft['specific_location']}\n"
        f"🗺️ Maps: {draft.get('maps_link') or 'Not provided'}\n"
        f"🏦 Payout: {draft['bank_name']} · {draft['bank_account_name']} · {masked_account}\n"
        f"📞 Contact: {draft['business_phone']}\n\n"
        "Submit this for admin review?"
    )
    keyboard = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    "✅ Submit application", callback_data="vendor_application_confirm"
                )
            ],
            [InlineKeyboardButton("⬅️ Back", callback_data="vendor_application_back")],
            [InlineKeyboardButton("❌ Cancel", callback_data="vendor_application_cancel")],
        ]
    )
    context.user_data.pop(_STATE_KEY, None)
    context.user_data[_STATE_KEY] = "confirm"
    await update.effective_message.reply_text(text, reply_markup=keyboard)


async def notify_admins(
    bot,
    *,
    vendor_id: int,
    applicant: str,
    telegram_username: str | None,
    telegram_id: int | None,
    application: dict,
) -> bool:
    """Send the submitted application and its license file to configured admins."""
    address = application.get("business_address") or ", ".join(
        value
        for value in (
            application.get("region"),
            application.get("city"),
            application.get("subcity"),
            application.get("specific_location"),
        )
        if value
    )
    review_text = (
        "🏪 NEW VENDOR APPLICATION\n\n"
        f"Application ID: {vendor_id}\n"
        f"Applicant: {applicant} · user {telegram_id} · @{telegram_username or 'not set'}\n"
        f"Store: {application['business_name']}\n"
        f"License: {application['business_license']}\n"
        f"TIN: {application['tin_number']}\n"
        f"Document type: {application['license_document_type']}\n"
        f"Category: {application['business_category']}\n"
        f"Address: {address}\n"
        f"Maps: {application.get('maps_link') or 'Not provided'}\n"
        f"Contact: {application['business_phone']}\n"
        f"Bank: {application['bank_name']}\n"
        f"Account name: {application['bank_account_name']}\n"
        f"Account number: {application['bank_account_number']}"
    )
    keyboard = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    "✅ Approve", callback_data=f"admin_approve_vendor_{vendor_id}"
                ),
                InlineKeyboardButton("❌ Reject", callback_data=f"admin_reject_vendor_{vendor_id}"),
            ]
        ]
    )
    notified = False
    for admin_id in settings.admin_ids_list:
        try:
            await bot.send_message(
                chat_id=admin_id,
                text=review_text[:4096],
                reply_markup=keyboard,
            )
            file_id = application["license_document_file_id"]
            if application["license_document_type"] == "photo":
                await bot.send_photo(chat_id=admin_id, photo=file_id)
            else:
                await bot.send_document(chat_id=admin_id, document=file_id)
            notified = True
        except TelegramError as exc:
            logger.error(
                "Could not notify admin %s about vendor application %s (%s)",
                admin_id,
                vendor_id,
                type(exc).__name__,
            )
    if not notified:
        logger.error("No admin received vendor application %s review notification", vendor_id)
    return notified


async def notify_applicant(bot, telegram_id: int | None, *, approved: bool) -> None:
    """Inform the applicant of the admin decision after the database commit."""
    if not telegram_id:
        return
    message = (
        "🎉 Your vendor application has been approved. Your vendor account is now active."
        if approved
        else "Your vendor application was not approved. Please contact support if you need more information."
    )
    try:
        await bot.send_message(chat_id=telegram_id, text=message)
    except TelegramError as exc:
        logger.warning(
            "Could not notify vendor user %s about %s (%s)",
            telegram_id,
            "approval" if approved else "rejection",
            type(exc).__name__,
        )


async def application_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Submit or cancel the completed application."""
    query = update.callback_query
    if not await answer_callback_query(query):
        return ConversationHandler.END
    if query.data == "vendor_application_cancel":
        context.user_data.pop(_DRAFT_KEY, None)
        context.user_data.pop(_STATE_KEY, None)
        await query.edit_message_text("Vendor application cancelled.")
        return ConversationHandler.END
    if context.user_data.get(_STATE_KEY) != "confirm":
        await query.edit_message_text(
            "This application has expired. Please start again from Profile."
        )
        return ConversationHandler.END

    tg_user = update.effective_user
    draft = context.user_data.get(_DRAFT_KEY, {})
    missing_step = await _resume_missing_step(
        update,
        context,
        draft,
        edit_message=True,
    )
    if missing_step is not None:
        return missing_step

    application_data = {
        **draft,
        "business_address": ", ".join(
            (draft["region"], draft["city"], draft["subcity"], draft["specific_location"])
        ),
        "business_phone": draft["business_phone"],
    }
    try:
        validated = VendorApplicationCreate.model_validate(application_data)
        async with transaction_session() as db:
            user = await UserRepository(db).get_by_telegram(tg_user.id)
            if not user:
                raise ValueError("The Telegram account is not registered")
            vendor = await VendorService(db).create_vendor(
                user.id,
                validated,
                notify_admins_on_event=False,
            )
            vendor_id = vendor.id
            applicant = user.full_name
            telegram_username = user.username
            telegram_id = user.telegram_id
    except (SchemaValidationError, ValueError) as exc:
        logger.warning(
            "Vendor application validation failed for Telegram user %s: %s", tg_user.id, exc
        )
        await query.edit_message_text(
            "❌ Some details could not be validated. Please cancel and submit the application again."
        )
        context.user_data.pop(_DRAFT_KEY, None)
        context.user_data.pop(_STATE_KEY, None)
        return ConversationHandler.END

    context.user_data.pop(_DRAFT_KEY, None)
    context.user_data.pop(_STATE_KEY, None)
    await query.edit_message_text("✅ Application submitted. We'll notify you after admin review.")

    try:
        from infrastructure.workers.tasks import send_vendor_application_review_task

        send_vendor_application_review_task.delay(vendor_id)
    except Exception as exc:
        logger.warning(
            "Could not queue vendor review notification %s (%s); scheduling local delivery",
            vendor_id,
            type(exc).__name__,
        )

        async def send_review_fallback() -> None:
            try:
                await notify_admins(
                    context.bot,
                    vendor_id=vendor_id,
                    applicant=applicant,
                    telegram_username=telegram_username,
                    telegram_id=telegram_id,
                    application=application_data,
                )
            except Exception:
                logger.exception("Could not send vendor review notification %s", vendor_id)

        task = asyncio.create_task(
            send_review_fallback(),
            name=f"vendor-review-{vendor_id}",
        )
        _notification_fallback_tasks.add(task)
        task.add_done_callback(_notification_fallback_tasks.discard)
    return ConversationHandler.END


async def cancel_application(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancel a vendor application from the /cancel command."""
    context.user_data.pop(_DRAFT_KEY, None)
    context.user_data.pop(_STATE_KEY, None)
    await update.effective_message.reply_text("Vendor application cancelled.")
    return ConversationHandler.END


__all__ = [
    "VENDOR_CONFIRM_STATE",
    "VENDOR_STEP_COUNT",
    "application_callback",
    "application_choice_callback",
    "application_navigation_callback",
    "cancel_application",
    "handle_document",
    "handle_text",
    "notify_admins",
    "notify_applicant",
    "start_application",
]
