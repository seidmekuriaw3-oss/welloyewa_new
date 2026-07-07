# ============================
# WOLLOYEWA STORE BOT - ADMIN TEXT/PHOTO INPUT HANDLER
# ============================
"""
State-based text and photo input handler for admin multi-step flows.
Registered in dispatcher.py *before* the general text catch-all.
State is stored in ``context.user_data["admin_state"]``.

States
------
add_product_name          → waiting for product name
add_product_price         → waiting for price in ETB
add_product_stock         → waiting for stock quantity
add_category_name         → waiting for new category name
edit_category_name        → waiting for updated category name
waiting_product_image     → waiting for a photo to attach to a product
                            (product id in user_data["admin_image_product_id"])
waiting_addphoto_pick     → admin typed /addphoto, now waiting to pick product via text search
"""

import io
import csv
import os
import uuid
import time

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from telegram.error import BadRequest

from core.logger import logger
from core.config import settings
from apps.products.services import ProductService, CategoryService
from apps.products.schemas import ProductCreate, CategoryCreate, CategoryUpdate
from infrastructure.database.session import get_db_session

# Directory served at /app/static/uploads/
_UPLOADS_DIR = os.path.join(
    os.path.dirname(__file__), "..", "..", "web_app", "static", "uploads"
)
os.makedirs(_UPLOADS_DIR, exist_ok=True)


# ── helpers ───────────────────────────────────────────────────────────────────

def _is_admin(update: Update) -> bool:
    return update.effective_user.id in settings.admin_ids_list


def _cancel_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("❌ ሰርዝ", callback_data="admin_products")]
    ])


def _img_done_keyboard(product_id: int, total: int) -> InlineKeyboardMarkup:
    """Keyboard shown after a successful image upload."""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(
            "📷 ሌላ ፎቶ ጨምር",
            callback_data=f"admin_prompt_image_{product_id}",
        )],
        [InlineKeyboardButton(
            f"🖼️ ሁሉንም ምስሎች ({total}) ይዩ",
            callback_data=f"admin_add_image_{product_id}",
        )],
        [InlineKeyboardButton("🔙 ምስሎች ማስተዳደር", callback_data="admin_product_images")],
    ])


# ── /addphoto command ─────────────────────────────────────────────────────────

async def addphoto_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    /addphoto [product_id]
    If product_id is given → immediately enter waiting_product_image state.
    Otherwise → show a searchable product list so admin can pick one.
    """
    if not _is_admin(update):
        return

    args = context.args or []
    if args:
        try:
            product_id = int(args[0])
        except ValueError:
            await update.message.reply_text(
                "⚠️ ልክ ያልሆነ ID። ምሳሌ: `/addphoto 5`",
                parse_mode="Markdown",
            )
            return

        # Verify product exists
        async for db in get_db_session():
            svc = ProductService(db)
            product = await svc.product_repo.get(product_id)
            break

        if not product:
            await update.message.reply_text(f"❌ ምርት ID {product_id} አልተገኘም።")
            return

        context.user_data["admin_state"] = "waiting_product_image"
        context.user_data["admin_image_product_id"] = product_id
        name = product.name_am or product.name
        img_count = len(product.images or [])

        await update.message.reply_text(
            f"📷 *ፎቶ ለ: {name}*\n"
            f"_(ያሉ ምስሎች: {img_count})_\n\n"
            "አሁን ፎቶ/ፎቶዎቹን ላኩ ⬇️\n"
            "_(ሰርዝ ለማድረግ ❌ ይጫኑ)_",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("❌ ሰርዝ", callback_data=f"admin_add_image_{product_id}")]
            ]),
        )
        return

    # No ID given — show first page of products
    await _show_addphoto_picker(update, context, page=1)


async def _show_addphoto_picker(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    page: int = 1,
    q: str = "",
) -> None:
    """Show a paginated/searchable product picker for /addphoto."""
    page_size = 8

    async for db in get_db_session():
        svc = ProductService(db)
        if q:
            products = await svc.search_products(q, limit=page_size)
            total = len(products)
        else:
            products, total = await svc.product_repo.get_all_with_count(
                limit=page_size,
                offset=(page - 1) * page_size,
                order_by="created_at",
                order_desc=True,
            )
        break

    if not products:
        msg = f"🔍 '*{q}*' ምርት አልተገኘም።" if q else "📦 ምንም ምርቶች አልተገኙም።"
        await update.message.reply_text(msg, parse_mode="Markdown")
        return

    total_pages = max(1, (total + page_size - 1) // page_size)
    context.user_data["admin_state"] = "waiting_addphoto_pick"
    context.user_data["addphoto_page"] = page

    text = "🖼️ *ምስል የሚጨምሩለትን ምርት ይምረጡ:*\n_(ወይም ስሙን ይፈልጉ — ጽሑፍ ያስገቡ)_\n\n"

    keyboard = []
    for p in products:
        img_n = len(p.images or [])
        icon = "🖼️" if img_n else "📦"
        label = (p.name_am or p.name)[:30]
        keyboard.append([InlineKeyboardButton(
            f"{icon} {label}  [{img_n}📷]",
            callback_data=f"admin_prompt_image_{p.id}",
        )])

    nav = []
    if page > 1:
        nav.append(InlineKeyboardButton("◀️", callback_data=f"addphoto_page_{page-1}"))
    if page < total_pages:
        nav.append(InlineKeyboardButton("▶️", callback_data=f"addphoto_page_{page+1}"))
    if nav:
        keyboard.append(nav)

    keyboard.append([InlineKeyboardButton("❌ ሰርዝ", callback_data="admin_products")])

    msg = update.message or (update.callback_query.message if update.callback_query else None)
    if msg:
        await msg.reply_text(
            text,
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard),
        )


# ── main text-input entry point ───────────────────────────────────────────────

async def handle_admin_text_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Called by the admin MessageHandler registered in dispatcher.py.
    Only runs when context.user_data["admin_state"] is set.
    """
    if not _is_admin(update):
        return

    state = context.user_data.get("admin_state")
    if not state:
        return

    text = (update.message.text or "").strip()

    # ── Add Product flow ──────────────────────────────────────────────────────
    if state == "add_product_name":
        if not text:
            await update.message.reply_text("⚠️ ስም ባዶ መሆን አይችልም። እባክዎ ይሞክሩ።")
            return
        context.user_data["new_product_name"] = text
        context.user_data["admin_state"] = "add_product_price"
        await update.message.reply_text(
            f"✅ ስም ተቀበለ: *{text}*\n\n💰 አሁን ዋጋ (ETB) ያስገቡ:\nምሳሌ: `150.50`",
            parse_mode="Markdown",
            reply_markup=_cancel_keyboard(),
        )

    elif state == "add_product_price":
        try:
            price = float(text.replace(",", ""))
            if price <= 0:
                raise ValueError
        except ValueError:
            await update.message.reply_text("⚠️ ዋጋው ልክ አይደለም (ምሳሌ: `150.50`):", parse_mode="Markdown")
            return
        context.user_data["new_product_price"] = price
        context.user_data["admin_state"] = "add_product_stock"
        await update.message.reply_text(
            f"✅ ዋጋ: *{price:.2f} ETB*\n\n📦 ክምችቱን ያስገቡ (ምሳሌ: `50`):",
            parse_mode="Markdown",
            reply_markup=_cancel_keyboard(),
        )

    elif state == "add_product_stock":
        try:
            stock = int(text)
            if stock < 0:
                raise ValueError
        except ValueError:
            await update.message.reply_text("⚠️ ክምችቱ ልክ አይደለም (ምሳሌ: `50`):", parse_mode="Markdown")
            return
        context.user_data["new_product_stock"] = stock
        context.user_data["admin_state"] = None

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
                "⚠️ ምድቦች አልተገኙም። ምድብ ሳይሆን ፍጠር:",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("📦 ምድብ ሳይሆን ፍጠር", callback_data="admin_cat_pick_0")],
                    [InlineKeyboardButton("❌ ሰርዝ", callback_data="admin_products")],
                ]),
            )
            return

        keyboard = []
        for cat in categories[:20]:
            keyboard.append([InlineKeyboardButton(cat.name, callback_data=f"admin_cat_pick_{cat.id}")])
        keyboard.append([InlineKeyboardButton("❌ ሰርዝ", callback_data="admin_products")])
        await update.message.reply_text(
            f"✅ ክምችት: *{stock}*\n\n📁 ምድቡን ይምረጡ:",
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
                f"✅ ምድቡ ተፈጠረ!\n• ስም: *{cat.name}*\n• ID: {cat.id}",
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
                f"✅ ምድቡ ተዘምኗል!\n• አዲስ ስም: *{cat.name}*\n• ID: {cat.id}",
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

    # ── /addphoto search ──────────────────────────────────────────────────────
    elif state == "waiting_addphoto_pick":
        # Admin typed a search term while in product picker
        context.user_data["admin_state"] = None
        await _show_addphoto_picker(update, context, page=1, q=text)

    else:
        logger.warning("Unknown admin_state: %s", state)
        context.user_data["admin_state"] = None


# ── Photo handler ─────────────────────────────────────────────────────────────

async def handle_admin_photo_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handles photo messages from admins.

    Two cases:
    1. admin_state == 'waiting_product_image'  → download & attach to product
    2. No state → ask which product to attach to (show picker)
    """
    if not _is_admin(update):
        return

    state = context.user_data.get("admin_state")

    # ── Case 2: no active state — show product picker ─────────────────────────
    if state != "waiting_product_image":
        # Save the photo file_id so we can reuse it after the admin picks a product
        photos = update.message.photo
        if photos:
            largest = max(photos, key=lambda p: p.file_size or 0)
            context.user_data["pending_photo_file_id"] = largest.file_id

        context.user_data["admin_state"] = "waiting_addphoto_pick"
        await update.message.reply_text(
            "📷 *ፎቶ ተቀበለ!*\n\n"
            "ምን ምርት ላይ ያስቀምጡት?\n"
            "_(ስሙን ይፈልጉ ወይም ከዚህ ይምረጡ)_",
            parse_mode="Markdown",
        )
        await _show_addphoto_picker(update, context, page=1)
        return

    # ── Case 1: waiting_product_image — download and save ────────────────────
    product_id = context.user_data.get("admin_image_product_id")
    if not product_id:
        await update.message.reply_text("❌ ምርቱ ID ጠፍቷል። /addphoto ያሂዱ።")
        context.user_data["admin_state"] = None
        return

    photos = update.message.photo
    if not photos:
        await update.message.reply_text("⚠️ ፎቶ አልተቀበለም። ዳግም ይሞክሩ።")
        return

    largest = max(photos, key=lambda p: p.file_size or 0)

    try:
        tg_file = await context.bot.get_file(largest.file_id)
        filename = f"prod_{product_id}_{int(time.time())}_{uuid.uuid4().hex[:6]}.jpg"
        save_path = os.path.join(_UPLOADS_DIR, filename)
        await tg_file.download_to_drive(save_path)
        url = f"/app/static/uploads/{filename}"

        async for db in get_db_session():
            svc = ProductService(db)
            product = await svc.product_repo.get(product_id)
            if not product:
                raise ValueError(f"Product {product_id} not found")
            existing = list(product.images or [])
            existing.append(url)
            await svc.product_repo.update(product_id, {"images": existing})
            prod_name = product.name_am or product.name
            break

        # Keep state open so admin can send more photos
        # (state stays "waiting_product_image", product id stays set)

        await update.message.reply_photo(
            photo=largest.file_id,
            caption=(
                f"✅ *ምስሉ ተጨምሯል!*\n\n"
                f"🛍️ {prod_name}\n"
                f"🖼️ ጠቅላላ ምስሎች: *{len(existing)}*\n"
                f"📎 `{url}`"
            ),
            parse_mode="Markdown",
            reply_markup=_img_done_keyboard(product_id, len(existing)),
        )
        logger.info("Image saved: product=%s path=%s total=%s", product_id, url, len(existing))

    except Exception as exc:
        logger.error("Photo upload product=%s error=%s", product_id, exc)
        await update.message.reply_text(
            "❌ ምስሉን ለማስቀመጥ ስህተት ተፈጥሯል።\nዳግም ፎቶ ይሞክሩ ወይም ሰርዝ:",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("❌ ሰርዝ", callback_data="admin_product_images")]
            ]),
        )


__all__ = ["handle_admin_text_input", "handle_admin_photo_input", "addphoto_command"]
