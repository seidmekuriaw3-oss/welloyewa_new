# ============================
# WOLLOYEWA STORE BOT - ADMIN TEXT-INPUT HANDLER
# ============================
"""
State-based text-input handler for admin multi-step flows.

Registered in dispatcher.py *before* the general text catch-all.
State is stored in ``context.user_data["admin_state"]``.

States
------
add_product_name    → waiting for product name (Amharic/English)
add_product_price   → waiting for price in ETB (numeric)
add_product_stock   → waiting for stock quantity (int)
add_category_name   → waiting for new category name
edit_category_name  → waiting for updated category name
                       (category id stored in user_data["admin_cat_id"])
"""

import io
import csv
import os
import uuid
import time

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from core.logger import logger
from core.config import settings
from apps.products.services import ProductService, CategoryService
from apps.products.schemas import ProductCreate, CategoryCreate, CategoryUpdate
from infrastructure.database.session import get_db_session

# Directory to store uploaded product images (served at /app/static/uploads/)
_UPLOADS_DIR = os.path.join(
    os.path.dirname(__file__), "..", "..", "web_app", "static", "uploads"
)
os.makedirs(_UPLOADS_DIR, exist_ok=True)


# ── helpers ──────────────────────────────────────────────────────────────────

def _is_admin(update: Update) -> bool:
    return update.effective_user.id in settings.admin_ids_list


def _cancel_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("❌ ሰርዝ", callback_data="admin_products")]
    ])


async def _cancel(update: Update, state_key: str = "admin_state") -> None:
    """Clear state and return to products panel."""
    # Just clear — dashboard router will handle the cancel button


# ── main entry point ─────────────────────────────────────────────────────────

async def handle_admin_text_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Called by the admin MessageHandler registered in dispatcher.py.
    Only runs when ``context.user_data["admin_state"]`` is set.
    """
    if not _is_admin(update):
        return  # not admin — let the normal text handler deal with it

    state = context.user_data.get("admin_state")
    if not state:
        return  # no active admin state

    text = (update.message.text or "").strip()

    # ── Add Product flow ──────────────────────────────────────────────────────
    if state == "add_product_name":
        if not text:
            await update.message.reply_text("⚠️ ስም ባዶ መሆን አይችልም። እባክዎ ይሞክሩ።")
            return
        context.user_data["new_product_name"] = text
        context.user_data["admin_state"] = "add_product_price"
        await update.message.reply_text(
            f"✅ ስም ተቀበለ: *{text}*\n\n"
            "💰 አሁን የምርቱን ዋጋ (ETB) ያስገቡ:\n"
            "ምሳሌ: `150.50`",
            parse_mode="Markdown",
            reply_markup=_cancel_keyboard(),
        )

    elif state == "add_product_price":
        try:
            price = float(text.replace(",", ""))
            if price <= 0:
                raise ValueError
        except ValueError:
            await update.message.reply_text("⚠️ ዋጋው ልክ አይደለም። ቁጥር ያስገቡ (ምሳሌ: `150.50`):", parse_mode="Markdown")
            return
        context.user_data["new_product_price"] = price
        context.user_data["admin_state"] = "add_product_stock"
        await update.message.reply_text(
            f"✅ ዋጋ: *{price:.2f} ETB*\n\n"
            "📦 አሁን ክምችቱን (ቁጥር) ያስገቡ:\n"
            "ምሳሌ: `50`",
            parse_mode="Markdown",
            reply_markup=_cancel_keyboard(),
        )

    elif state == "add_product_stock":
        try:
            stock = int(text)
            if stock < 0:
                raise ValueError
        except ValueError:
            await update.message.reply_text("⚠️ ክምችቱ ልክ አይደለም። ቁጥር ያስገቡ (ምሳሌ: `50`):", parse_mode="Markdown")
            return
        context.user_data["new_product_stock"] = stock
        context.user_data["admin_state"] = None  # clear — next step uses callbacks

        # Show category picker
        try:
            async for db in get_db_session():
                cat_service = CategoryService(db)
                categories = await cat_service.get_all_categories()
                break
        except Exception as exc:
            logger.error("Category fetch error: %s", exc)
            categories = []

        if not categories:
            await update.message.reply_text(
                "⚠️ ምድቦች አልተገኙም። ምርቱን ከምድብ ሳይሆን ለማስገባት ከዚህ ይቀጥሉ:",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("📦 ምድብ ሳይሆን ፍጠር", callback_data="admin_cat_pick_0")],
                    [InlineKeyboardButton("❌ ሰርዝ", callback_data="admin_products")],
                ]),
            )
            return

        keyboard = []
        for cat in categories[:20]:
            keyboard.append([InlineKeyboardButton(
                cat.name, callback_data=f"admin_cat_pick_{cat.id}"
            )])
        keyboard.append([InlineKeyboardButton("❌ ሰርዝ", callback_data="admin_products")])

        await update.message.reply_text(
            f"✅ ክምችት: *{stock}*\n\n"
            "📁 ምድቡን ይምረጡ:",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard),
        )

    # ── Add Category flow ─────────────────────────────────────────────────────
    elif state == "add_category_name":
        if not text:
            await update.message.reply_text("⚠️ ስም ባዶ መሆን አይችልም።")
            return
        context.user_data["admin_state"] = None
        try:
            async for db in get_db_session():
                cat_service = CategoryService(db)
                cat = await cat_service.create_category(CategoryCreate(name=text))
                break
            await update.message.reply_text(
                f"✅ ምድቡ ተፈጠረ!\n\n"
                f"• ስም: *{cat.name}*\n"
                f"• ID: {cat.id}",
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔙 ወደ ምድቦች", callback_data="admin_categories")]
                ]),
            )
        except Exception as exc:
            logger.error("Create category error: %s", exc)
            await update.message.reply_text(
                "❌ ምድቡን ለመፍጠር ስህተት ተፈጥሯል።",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔙 ወደ ምድቦች", callback_data="admin_categories")]
                ]),
            )

    # ── Edit Category flow ────────────────────────────────────────────────────
    elif state == "edit_category_name":
        if not text:
            await update.message.reply_text("⚠️ ስም ባዶ መሆን አይችልም።")
            return
        cat_id = context.user_data.get("admin_cat_id")
        context.user_data["admin_state"] = None
        context.user_data.pop("admin_cat_id", None)
        if not cat_id:
            await update.message.reply_text("❌ ምድቡ ID ጠፍቷል። እባክዎ ዳግም ይሞክሩ።")
            return
        try:
            async for db in get_db_session():
                cat_service = CategoryService(db)
                cat = await cat_service.update_category(cat_id, CategoryUpdate(name=text))
                break
            await update.message.reply_text(
                f"✅ ምድቡ ተዘምኗል!\n\n"
                f"• አዲስ ስም: *{cat.name}*\n"
                f"• ID: {cat.id}",
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔙 ወደ ምድቦች", callback_data="admin_categories")]
                ]),
            )
        except Exception as exc:
            logger.error("Update category error: %s", exc)
            await update.message.reply_text(
                "❌ ምድቡን ለማዘምን ስህተት ተፈጥሯል።",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔙 ወደ ምድቦች", callback_data="admin_categories")]
                ]),
            )

    # Unknown state — clear it
    else:
        logger.warning("Unknown admin_state: %s", state)
        context.user_data["admin_state"] = None


# ── Photo handler (called from dispatcher group 0) ───────────────────────────

async def handle_admin_photo_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handles photo messages sent by admins when admin_state == 'waiting_product_image'.
    Downloads the largest photo size, saves to static/uploads/, updates product.images.
    """
    if not _is_admin(update):
        return

    state = context.user_data.get("admin_state")
    if state != "waiting_product_image":
        return

    product_id = context.user_data.get("admin_image_product_id")
    if not product_id:
        await update.message.reply_text("❌ ምርቱ ID ጠፍቷል። እባክዎ ዳግም ይሞክሩ።")
        context.user_data["admin_state"] = None
        return

    # Get the largest available photo
    photos = update.message.photo
    if not photos:
        await update.message.reply_text("⚠️ ፎቶ አልተቀበለም። እባክዎ ዳግም ይሞክሩ።")
        return

    largest = max(photos, key=lambda p: p.file_size or 0)

    try:
        # Download from Telegram
        tg_file = await context.bot.get_file(largest.file_id)
        filename = f"prod_{product_id}_{int(time.time())}_{uuid.uuid4().hex[:6]}.jpg"
        save_path = os.path.join(_UPLOADS_DIR, filename)
        await tg_file.download_to_drive(save_path)

        url = f"/app/static/uploads/{filename}"

        # Update product images list in DB
        async for db in get_db_session():
            product_service = ProductService(db)
            product = await product_service.product_repo.get(product_id)
            if not product:
                raise ValueError(f"Product {product_id} not found")
            existing = list(product.images or [])
            existing.append(url)
            await product_service.product_repo.update(product_id, {"images": existing})
            break

        context.user_data["admin_state"] = None
        context.user_data.pop("admin_image_product_id", None)

        await update.message.reply_photo(
            photo=largest.file_id,
            caption=(
                f"✅ *ምስሉ ተጨምሯል!*\n\n"
                f"• ምርት ID: {product_id}\n"
                f"• URL: `{url}`\n"
                f"• ጠቅላላ ምስሎች: {len(existing)}"
            ),
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🖼️ ምስሎቹን ይዩ", callback_data=f"admin_add_image_{product_id}")],
                [InlineKeyboardButton("🔙 ወደ ምርቶች", callback_data="admin_product_images")],
            ]),
        )
        logger.info("Image saved for product %s → %s", product_id, url)

    except Exception as exc:
        logger.error("Photo upload for product %s failed: %s", product_id, exc)
        await update.message.reply_text(
            "❌ ምስሉን ለማስቀመጥ ስህተት ተፈጥሯል። እባክዎ ዳግም ይሞክሩ።",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("❌ ሰርዝ", callback_data="admin_product_images")]
            ]),
        )


__all__ = ["handle_admin_text_input", "handle_admin_photo_input"]
