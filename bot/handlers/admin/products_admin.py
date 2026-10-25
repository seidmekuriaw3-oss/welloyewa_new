# ============================
# WOLLOYEWA STORE BOT - ADMIN PRODUCTS HANDLER
# ============================
"""Admin handlers for product management."""

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.helpers import escape_markdown
from telegram.ext import ContextTypes

from apps.products.schemas import ProductCreate
from apps.products.services import CategoryService, ProductService
from core.constants import ProductStatus
from core.exceptions import ValidationError
from core.logger import logger
from core.utils.currency import format_etb
from infrastructure.database.session import transaction_session

# ── helpers ───────────────────────────────────────────────────────────────────


def _products_back_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [[InlineKeyboardButton("🔙 ወደ ምርት አስተዳደር", callback_data="admin_products_back")]]
    )


STATUS_EMOJI = {
    "active": "✅",
    "inactive": "⚪",
    "pending": "⏳",
    "rejected": "❌",
}


# ── Panels ────────────────────────────────────────────────────────────────────


async def products_admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show admin products management panel."""
    query = update.callback_query

    keyboard = [
        [InlineKeyboardButton("📋 ሁሉንም ምርቶች", callback_data="admin_list_products")],
        [InlineKeyboardButton("+ አዲስ ምርት", callback_data="admin_add_product")],
        [InlineKeyboardButton("📁 ምድቦች", callback_data="admin_categories")],
        [InlineKeyboardButton("🖼️ ምስሎች ማስተዳደር", callback_data="admin_product_images")],
        [InlineKeyboardButton("⏳ በመጠባበቅ ላይ", callback_data="admin_pending_products")],
        [InlineKeyboardButton("🔙 ወደ አስተዳደር", callback_data="admin_back")],
    ]

    await query.message.edit_text(
        "📦 *የምርት አስተዳደር*\n\nከዚህ በታች ያሉትን አማራጮች ይምረጡ።",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )


async def list_products(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """List all products with pagination."""
    query = update.callback_query
    page = context.user_data.get("admin_products_page", 1)
    page_size = 8

    try:
        async with transaction_session() as db:
            product_service = ProductService(db)
            products, total = await product_service.product_repo.get_all_with_count(
                filters={"is_deleted": False},
                limit=page_size,
                offset=(page - 1) * page_size,
                order_by="created_at",
                order_desc=True,
            )
    except Exception as exc:
        logger.error("list_products error: %s", exc)
        await query.message.edit_text(
            "❌ ምርቶችን ለማምጣት ስህተት ተፈጥሯል።",
            reply_markup=_products_back_keyboard(),
        )
        return

    if not products:
        await query.message.edit_text(
            "📦 ምንም ምርቶች አልተገኙም።",
            reply_markup=_products_back_keyboard(),
        )
        return

    total_pages = max(1, (total + page_size - 1) // page_size)
    text = f"📦 *ሁሉም ምርቶች* — ገጽ {page}/{total_pages} ({total} ጠቅላላ)\n\n"

    for p in products:
        emoji = STATUS_EMOJI.get(str(p.status), "📦")
        product_name = escape_markdown(str(p.name), version=1)
        text += (
            f"{emoji} *{product_name}* (ID:{p.id})\n"
            f"   💰 {format_etb(p.price)} | 📦 ክምችት: {p.stock_quantity}\n\n"
        )

    nav = []
    if page > 1:
        nav.append(InlineKeyboardButton("◀️ ቀዳሚ", callback_data="admin_products_page_prev"))
    if page < total_pages:
        nav.append(InlineKeyboardButton("ቀጣይ ▶️", callback_data="admin_products_page_next"))

    keyboard = []
    if nav:
        keyboard.append(nav)
    keyboard.append([InlineKeyboardButton("🔙 ወደ ምርት አስተዳደር", callback_data="admin_products_back")])

    await query.message.edit_text(
        text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def list_pending_products(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """List products pending admin approval — each with Approve/Reject buttons."""
    query = update.callback_query

    try:
        async with transaction_session() as db:
            product_service = ProductService(db)
            products = await product_service.product_repo.get_all(
                filters={"status": ProductStatus.PENDING, "is_deleted": False},
                order_by="created_at",
                order_desc=True,
                limit=20,
            )
    except Exception as exc:
        logger.error("list_pending_products error: %s", exc)
        await query.message.edit_text(
            "❌ ምርቶችን ለማምጣት ስህተት ተፈጥሯል።",
            reply_markup=_products_back_keyboard(),
        )
        return

    if not products:
        await query.message.edit_text(
            "✅ በመጠባበቅ ላይ ያሉ ምርቶች የሉም።",
            reply_markup=_products_back_keyboard(),
        )
        return

    text = f"⏳ *በመጠባበቅ ላይ ያሉ ምርቶች* ({len(products)})\n\n"
    keyboard = []

    for p in products[:10]:  # cap at 10 to avoid message size limit
        product_name = escape_markdown(str(p.name), version=1)
        text += (
            f"📦 *{product_name}* (ID:{p.id})\n"
            f"   👤 ሻጭ: {p.vendor_id} | 💰 {format_etb(p.price)}\n"
            f"   📅 {p.created_at.strftime('%Y-%m-%d')}\n\n"
        )
        keyboard.append(
            [
                InlineKeyboardButton(
                    f"✅ {p.name[:20]}", callback_data=f"admin_approve_product_{p.id}"
                ),
                InlineKeyboardButton("❌ ውድቅ", callback_data=f"admin_reject_product_{p.id}"),
            ]
        )

    keyboard.append([InlineKeyboardButton("🔙 ወደ ምርት አስተዳደር", callback_data="admin_products_back")])

    await query.message.edit_text(
        text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def manage_categories(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show category list with per-category Edit and Delete buttons."""
    query = update.callback_query

    try:
        async with transaction_session() as db:
            category_service = CategoryService(db)
            categories = await category_service.get_all_categories()
    except Exception as exc:
        logger.error("manage_categories error: %s", exc)
        categories = []

    text = f"📁 *ምድቦች* ({len(categories)})\n\n"

    keyboard = []
    for cat in categories[:15]:
        category_name = escape_markdown(str(cat.name), version=1)
        text += f"• *{category_name}* (ID:{cat.id})\n"
        keyboard.append(
            [
                InlineKeyboardButton(
                    f"✏️ {cat.name[:18]}", callback_data=f"admin_cat_edit_{cat.id}"
                ),
                InlineKeyboardButton("🗑️ ሰርዝ", callback_data=f"admin_cat_del_{cat.id}"),
            ]
        )

    keyboard.append([InlineKeyboardButton("+ አዲስ ምድብ", callback_data="admin_add_category")])
    keyboard.append([InlineKeyboardButton("🔙 ወደ ምርት አስተዳደር", callback_data="admin_products_back")])

    await query.message.edit_text(
        text or "📁 ምንም ምድቦች አልተገኙም።",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )


# ── Action functions (called by dashboard router) ─────────────────────────────


async def start_add_product(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Begin add-product multi-step flow."""
    query = update.callback_query
    # Clear any leftover state
    context.user_data["admin_state"] = "add_product_name"
    for key in ("new_product_name", "new_product_price", "new_product_stock"):
        context.user_data.pop(key, None)

    await query.message.reply_text(
        "+ *አዲስ ምርት ማስገባት*\n\n"
        "📝 የምርቱን ስም ያስገቡ (Amharic ወይም English):\n\n"
        "❌ ለመሰረዝ /cancel ይላኩ",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(
            [[InlineKeyboardButton("❌ ሰርዝ", callback_data="admin_products")]]
        ),
    )


async def start_add_category(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Begin add-category flow."""
    query = update.callback_query
    context.user_data["admin_state"] = "add_category_name"

    await query.message.reply_text(
        "+ *አዲስ ምድብ ማስገባት*\n\n" "📝 የምድቡን ስም ያስገቡ:",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(
            [[InlineKeyboardButton("❌ ሰርዝ", callback_data="admin_categories")]]
        ),
    )


async def start_edit_category(
    update: Update, context: ContextTypes.DEFAULT_TYPE, cat_id: int
) -> None:
    """Begin edit-category text flow for a specific category."""
    query = update.callback_query
    context.user_data["admin_state"] = "edit_category_name"
    context.user_data["admin_cat_id"] = cat_id

    await query.message.reply_text(
        f"✏️ *ምድብ ማርትዕ* (ID: {cat_id})\n\n" "📝 አዲሱን ስም ያስገቡ:",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(
            [[InlineKeyboardButton("❌ ሰርዝ", callback_data="admin_categories")]]
        ),
    )


async def confirm_delete_category(
    update: Update, context: ContextTypes.DEFAULT_TYPE, cat_id: int
) -> None:
    """Show delete-category confirmation panel."""
    query = update.callback_query

    await query.message.edit_text(
        f"🗑️ *ምድቡን ለመሰረዝ እርግጠኛ ነዎት?* (ID: {cat_id})\n\n" "⚠️ ይህ ድርጊት ሊቀለበስ አይችልም!",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        "✅ አዎ፣ ሰርዝ", callback_data=f"admin_cat_del_confirm_{cat_id}"
                    ),
                    InlineKeyboardButton("❌ አይ", callback_data="admin_categories"),
                ]
            ]
        ),
    )


async def do_delete_category(
    update: Update, context: ContextTypes.DEFAULT_TYPE, cat_id: int
) -> None:
    """Actually delete a category."""
    query = update.callback_query

    try:
        async with transaction_session() as db:
            cat_service = CategoryService(db)
            success = await cat_service.delete_category(cat_id)

        if success:
            await query.message.edit_text(
                f"✅ ምድቡ (ID: {cat_id}) ተሰርዟል።",
                reply_markup=InlineKeyboardMarkup(
                    [[InlineKeyboardButton("🔙 ወደ ምድቦች", callback_data="admin_categories")]]
                ),
            )
        else:
            await query.message.edit_text(
                f"❌ ምድቡ (ID: {cat_id}) አልተገኘም።",
                reply_markup=InlineKeyboardMarkup(
                    [[InlineKeyboardButton("🔙 ወደ ምድቦች", callback_data="admin_categories")]]
                ),
            )
    except ValidationError as exc:
        logger.warning("Delete category %s blocked: %s", cat_id, exc)
        await query.message.edit_text(
            f"⚠️ {exc}",
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("🔙 ወደ ምድቦች", callback_data="admin_categories")]]
            ),
        )
    except Exception as exc:
        logger.error("Delete category %s error: %s", cat_id, exc)
        await query.message.edit_text(
            "❌ ምድቡን ለመሰረዝ ስህተት ተፈጥሯል።",
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("🔙 ወደ ምድቦች", callback_data="admin_categories")]]
            ),
        )


async def do_approve_product(
    update: Update, context: ContextTypes.DEFAULT_TYPE, product_id: int
) -> None:
    """Approve a pending product."""
    query = update.callback_query

    try:
        async with transaction_session() as db:
            product_service = ProductService(db)
            product = await product_service.get_product(product_id)
            if product.status != ProductStatus.PENDING:
                raise ValueError(f"Product {product_id} is not pending approval")
            await product_service.product_repo.update(
                product_id, {"status": ProductStatus.ACTIVE}
            )
            if product.category_id is not None:
                await product_service.category_repo.update_product_count(product.category_id)
        await query.message.edit_text(
            f"✅ ምርቱ (ID: {product_id}) ፀድቋል!",
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("🔙 ወደ ምርቶች", callback_data="admin_pending_products")]]
            ),
        )
    except Exception as exc:
        logger.error("Approve product %s error: %s", product_id, exc)
        await query.message.edit_text(
            "❌ ምርቱን ለማጽደቅ ስህተት ተፈጥሯል።",
            reply_markup=_products_back_keyboard(),
        )


async def do_reject_product(
    update: Update, context: ContextTypes.DEFAULT_TYPE, product_id: int
) -> None:
    """Reject a pending product."""
    query = update.callback_query

    try:
        async with transaction_session() as db:
            product_service = ProductService(db)
            product = await product_service.get_product(product_id)
            if product.status != ProductStatus.PENDING:
                raise ValueError(f"Product {product_id} is not pending review")
            await product_service.product_repo.update(
                product_id, {"status": ProductStatus.REJECTED}
            )
        await query.message.edit_text(
            f"❌ ምርቱ (ID: {product_id}) ውድቅ ሆኗል።",
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("🔙 ወደ ምርቶች", callback_data="admin_pending_products")]]
            ),
        )
    except Exception as exc:
        logger.error("Reject product %s error: %s", product_id, exc)
        await query.message.edit_text(
            "❌ ምርቱን ውድቅ ለማድረግ ስህተት ተፈጥሯል።",
            reply_markup=_products_back_keyboard(),
        )


async def do_create_product_with_category(
    update: Update, context: ContextTypes.DEFAULT_TYPE, category_id: int
) -> None:
    """Ask the admin to choose an approved vendor for the new product."""
    query = update.callback_query

    name = context.user_data.get("new_product_name")
    price = context.user_data.get("new_product_price")
    stock = context.user_data.get("new_product_stock")

    if not name or price is None or stock is None:
        await query.message.edit_text(
            "❌ ምርቱን ለመፍጠር ያስፈለጉ ዝርዝሮች ጠፍተዋል። እባክዎ ዳግም ይሞክሩ።",
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("🔙 ወደ ምርቶች", callback_data="admin_products")]]
            ),
        )
        return

    try:
        async with transaction_session() as db:
            from apps.users.repository import VendorRepository

            vendors = await VendorRepository(db).get_approved_vendors(limit=100)
    except Exception as exc:
        logger.error("Load approved vendors for product creation failed: %s", exc)
        await query.message.edit_text(
            "❌ ሻጮችን ለማምጣት ስህተት ተፈጥሯል።",
            reply_markup=_products_back_keyboard(),
        )
        return

    if not vendors:
        await query.message.edit_text(
            "⚠️ የተፈቀደ ሻጭ አልተገኘም። ምርት ለመፍጠር በመጀመሪያ ሻጭ ያጽድቁ።",
            reply_markup=_products_back_keyboard(),
        )
        return

    context.user_data["new_product_category_id"] = category_id
    keyboard = [
        [
            InlineKeyboardButton(
                vendor.business_name[:50],
                callback_data=f"admin_vendor_pick_{vendor.id}_{category_id}",
            )
        ]
        for vendor in vendors[:50]
    ]
    keyboard.append(
        [InlineKeyboardButton("❌ ሰርዝ", callback_data="admin_products")]
    )
    await query.message.edit_text(
        "🏪 ምርቱን የሚያቀርበውን የተፈቀደ ሻጭ ይምረጡ:",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )


async def do_create_product_with_vendor(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    vendor_id: int,
    category_id: int,
) -> None:
    """Create an admin-entered product under a selected approved vendor."""
    query = update.callback_query
    name = context.user_data.get("new_product_name")
    price = context.user_data.get("new_product_price")
    stock = context.user_data.get("new_product_stock")
    if not name or price is None or stock is None:
        await query.message.edit_text(
            "❌ ምርቱን ለመፍጠር ያስፈለጉ ዝርዝሮች ጠፍተዋል። እባክዎ ዳግም ይሞክሩ።",
            reply_markup=_products_back_keyboard(),
        )
        return

    import re
    import uuid

    try:
        async with transaction_session() as db:
            from apps.users.repository import VendorRepository

            vendor = await VendorRepository(db).get_by_id(vendor_id)
            if not vendor or not vendor.is_approved:
                raise ValueError(f"Vendor {vendor_id} is not approved")
            product_service = ProductService(db)
            sku_base = re.sub(r"[^A-Za-z0-9]", "", name.upper())[:8] or "PROD"
            sku = f"{sku_base}-{uuid.uuid4().hex[:6].upper()}"
            product = await product_service.create_product(
                vendor_id=vendor_id,
                data=ProductCreate(
                    name=name,
                    price=price,
                    stock_quantity=stock,
                    category_id=category_id if category_id > 0 else None,
                    sku=sku,
                    status=ProductStatus.ACTIVE,
                ),
                admin_approved=True,
            )

        for key in (
            "new_product_name",
            "new_product_price",
            "new_product_stock",
            "new_product_category_id",
        ):
            context.user_data.pop(key, None)

        product_name = escape_markdown(str(product.name), version=1)
        await query.message.edit_text(
            f"✅ *ምርቱ ተፈጠረ!*\n\n"
            f"• ስም: *{product_name}*\n"
            f"• ዋጋ: {format_etb(product.price)}\n"
            f"• ክምችት: {product.stock_quantity}\n"
            f"• ID: {product.id}",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(
                [
                    [InlineKeyboardButton("📋 ምርቶችን ይዩ", callback_data="admin_list_products")],
                    [InlineKeyboardButton("🔙 ወደ ምርት አስተዳደር", callback_data="admin_products")],
                ]
            ),
        )
    except Exception as exc:
        logger.error("Create product error: %s", exc)
        await query.message.edit_text(
            "❌ ምርቱን ለመፍጠር ስህተት ተፈጥሯል። የተፈቀደ ሻጭ እና ምርት መረጃውን ያረጋግጡ።",
            reply_markup=_products_back_keyboard(),
        )


# ── Image management ──────────────────────────────────────────────────────────


async def list_products_for_images(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show paginated product list where each row has an 'Add Image' button."""
    query = update.callback_query
    page = context.user_data.get("admin_images_page", 1)
    page_size = 8

    try:
        async with transaction_session() as db:
            product_service = ProductService(db)
            products, total = await product_service.product_repo.get_all_with_count(
                filters={"is_deleted": False},
                limit=page_size,
                offset=(page - 1) * page_size,
                order_by="created_at",
                order_desc=True,
            )
    except Exception as exc:
        logger.error("list_products_for_images error: %s", exc)
        await query.message.edit_text(
            "❌ ምርቶችን ለማምጣት ስህተት ተፈጥሯል።",
            reply_markup=_products_back_keyboard(),
        )
        return

    if not products:
        await query.message.edit_text(
            "📦 ምንም ምርቶች አልተገኙም።",
            reply_markup=_products_back_keyboard(),
        )
        return

    total_pages = max(1, (total + page_size - 1) // page_size)
    text = f"🖼️ *ምስሎች ማስተዳደር* — ገጽ {page}/{total_pages}\n\nምርቱን ይምረጡ:\n\n"

    keyboard = []
    for p in products:
        img_count = len(p.images) if p.images else 0
        emoji = STATUS_EMOJI.get(str(p.status), "📦")
        keyboard.append(
            [
                InlineKeyboardButton(
                    f"{emoji} {p.name[:22]} 🖼️{img_count}",
                    callback_data=f"admin_add_image_{p.id}",
                )
            ]
        )

    nav = []
    if page > 1:
        nav.append(InlineKeyboardButton("◀️ ቀዳሚ", callback_data="admin_images_page_prev"))
    if page < total_pages:
        nav.append(InlineKeyboardButton("ቀጣይ ▶️", callback_data="admin_images_page_next"))
    if nav:
        keyboard.append(nav)
    keyboard.append([InlineKeyboardButton("🔙 ወደ ምርት አስተዳደር", callback_data="admin_products_back")])

    await query.message.edit_text(
        text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def show_product_images(
    update: Update, context: ContextTypes.DEFAULT_TYPE, product_id: int
) -> None:
    """
    Show current images for a product.
    - Sends each saved image as a real thumbnail (reply_photo) with a delete button.
    - Then sends a summary text message with 'Add Image' button.
    """
    query = update.callback_query

    try:
        async with transaction_session() as db:
            product_service = ProductService(db)
            product = await product_service.product_repo.get_by_id(product_id)
    except Exception as exc:
        logger.error("show_product_images error: %s", exc)
        await query.message.edit_text("❌ ምርቱ አልተገኘም።", reply_markup=_products_back_keyboard())
        return

    if not product:
        await query.message.edit_text("❌ ምርቱ አልተገኘም።", reply_markup=_products_back_keyboard())
        return

    name = product.name_am or product.name
    images = product.images or []
    chat_id = query.message.chat.id

    # ── Header message ──────────────────────────────────────────────────────
    header = f"🖼️ *{name}*\n" f"ID: {product_id} | ምስሎች: {len(images)}\n\n"
    if not images:
        header += "_ምንም ምስሎች የሉም — ከዚህ በታች ፎቶ ጨምር_"
    else:
        header += "_ምስሎቹ ከዚህ በታች ተቀምጠዋል። ለማስወገድ 🗑️ ይጫኑ።_"

    add_btn = InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("📷 ፎቶ ጨምር", callback_data=f"admin_prompt_image_{product_id}")],
            [InlineKeyboardButton("🔙 ወደ ምርቶች", callback_data="admin_product_images")],
        ]
    )

    # Edit current message to header
    try:
        await query.message.edit_text(header, parse_mode="Markdown", reply_markup=add_btn)
    except Exception:
        await query.message.reply_text(header, parse_mode="Markdown", reply_markup=add_btn)

    # ── Send each image as a real thumbnail ─────────────────────────────────
    for i, url in enumerate(images):
        del_kb = InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        f"🗑️ ምስል {i+1} ሰርዝ",
                        callback_data=f"admin_remove_image_{product_id}_{i}",
                    )
                ]
            ]
        )
        try:
            from bot.product_media import telegram_photo_source

            with telegram_photo_source(str(url)) as photo:
                await context.bot.send_photo(
                    chat_id=chat_id,
                    photo=photo,
                    caption=f"ምስል {i+1}/{len(images)}",
                    reply_markup=del_kb,
                )
        except Exception as e:
            logger.warning("Could not send thumbnail %s for product %s: %s", url, product_id, e)
            # Send as a text fallback with the URL
            await context.bot.send_message(
                chat_id=chat_id,
                text=f"🖼️ ምስል {i+1}: `{url}`",
                parse_mode="Markdown",
                reply_markup=del_kb,
            )


async def prompt_upload_image(
    update: Update, context: ContextTypes.DEFAULT_TYPE, product_id: int
) -> None:
    """Set admin state to waiting_product_image and ask for a photo."""
    query = update.callback_query
    context.user_data["admin_state"] = "waiting_product_image"
    context.user_data["admin_image_product_id"] = product_id

    await query.message.reply_text(
        f"📷 *ምርት ID {product_id} ምስል መጨምር*\n\n"
        "አሁን ምርቱን ፎቶ ይላኩ (Telegram ፎቶ እንጂ ፋይል አይደለም):\n\n"
        "❌ ለመሰርዝ 'ሰርዝ' ይላኩ",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(
            [[InlineKeyboardButton("❌ ሰርዝ", callback_data=f"admin_add_image_{product_id}")]]
        ),
    )


async def do_remove_product_image(
    update: Update, context: ContextTypes.DEFAULT_TYPE, product_id: int, img_index: int
) -> None:
    """Remove one image from a product by index."""
    query = update.callback_query

    try:
        async with transaction_session() as db:
            product_service = ProductService(db)
            product = await product_service.product_repo.get_by_id(product_id)
            if not product:
                raise ValueError("not found")
            images = list(product.images or [])
            if img_index < len(images):
                removed = images.pop(img_index)
                await product_service.product_repo.update(product_id, {"images": images})
                logger.info("Removed image %s from product %s", removed, product_id)
    except Exception as exc:
        logger.error("remove_image %s[%s] error: %s", product_id, img_index, exc)
        await query.answer("❌ ምስሉን ለማስወገድ ስህተት ተፈጥሯል።", show_alert=True)
        return

    await query.answer("✅ ምስሉ ተሰርዟል!")
    await show_product_images(update, context, product_id)


# ── legacy stub (dispatcher.py registers product_admin_callback for ^prod_admin_) ──


async def product_admin_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Legacy entry — all admin_ routing done in dashboard.admin_callback."""
    pass


__all__ = [
    "confirm_delete_category",
    "do_approve_product",
    "do_create_product_with_category",
    "do_delete_category",
    "do_reject_product",
    "do_remove_product_image",
    "list_pending_products",
    "list_products",
    "list_products_for_images",
    "manage_categories",
    "product_admin_callback",
    "products_admin_panel",
    "prompt_upload_image",
    "show_product_images",
    "start_add_category",
    "start_add_product",
    "start_edit_category",
]
