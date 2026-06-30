# ============================
# WOLLOYEWA STORE BOT - ADMIN PRODUCTS HANDLER
# ============================
"""Admin handlers for product management."""

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from datetime import datetime

from core.logger import logger
from core.utils.currency import format_etb
from apps.products.services import ProductService, CategoryService
from apps.products.schemas import ProductCreate
from infrastructure.database.session import get_db_session


# ── helpers ───────────────────────────────────────────────────────────────────

def _products_back_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔙 ወደ ምርት አስተዳደር", callback_data="admin_products_back")]
    ])


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
        [InlineKeyboardButton("📋 ሁሉንም ምርቶች",   callback_data="admin_list_products")],
        [InlineKeyboardButton("➕ አዲስ ምርት",       callback_data="admin_add_product")],
        [InlineKeyboardButton("📁 ምድቦች",          callback_data="admin_categories")],
        [InlineKeyboardButton("⏳ በመጠባበቅ ላይ",    callback_data="admin_pending_products")],
        [InlineKeyboardButton("🔙 ወደ አስተዳደር",     callback_data="admin_back")],
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
        async for db in get_db_session():
            product_service = ProductService(db)
            products, total = await product_service.product_repo.get_all_with_count(
                limit=page_size,
                offset=(page - 1) * page_size,
                order_by="created_at",
                order_desc=True,
            )
            break
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
        text += (
            f"{emoji} *{p.name}* (ID:{p.id})\n"
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
        async for db in get_db_session():
            product_service = ProductService(db)
            products = await product_service.product_repo.get_all(
                filters={"status": "pending"},
                order_by="created_at",
                order_desc=True,
                limit=20,
            )
            break
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
        text += (
            f"📦 *{p.name}* (ID:{p.id})\n"
            f"   👤 ሻጭ: {p.vendor_id} | 💰 {format_etb(p.price)}\n"
            f"   📅 {p.created_at.strftime('%Y-%m-%d')}\n\n"
        )
        keyboard.append([
            InlineKeyboardButton(f"✅ {p.name[:20]}", callback_data=f"admin_approve_product_{p.id}"),
            InlineKeyboardButton("❌ ውድቅ", callback_data=f"admin_reject_product_{p.id}"),
        ])

    keyboard.append([InlineKeyboardButton("🔙 ወደ ምርት አስተዳደር", callback_data="admin_products_back")])

    await query.message.edit_text(
        text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def manage_categories(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show category list with per-category Edit and Delete buttons."""
    query = update.callback_query

    try:
        async for db in get_db_session():
            category_service = CategoryService(db)
            categories = await category_service.get_all_categories()
            break
    except Exception as exc:
        logger.error("manage_categories error: %s", exc)
        categories = []

    text = f"📁 *ምድቦች* ({len(categories)})\n\n"

    keyboard = []
    for cat in categories[:15]:
        text += f"• *{cat.name}* (ID:{cat.id})\n"
        keyboard.append([
            InlineKeyboardButton(f"✏️ {cat.name[:18]}", callback_data=f"admin_cat_edit_{cat.id}"),
            InlineKeyboardButton("🗑️ ሰርዝ",             callback_data=f"admin_cat_del_{cat.id}"),
        ])

    keyboard.append([InlineKeyboardButton("➕ አዲስ ምድብ", callback_data="admin_add_category")])
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
        "➕ *አዲስ ምርት ማስገባት*\n\n"
        "📝 የምርቱን ስም ያስገቡ (Amharic ወይም English):\n\n"
        "❌ ለመሰረዝ /cancel ይላኩ",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("❌ ሰርዝ", callback_data="admin_products")]
        ]),
    )


async def start_add_category(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Begin add-category flow."""
    query = update.callback_query
    context.user_data["admin_state"] = "add_category_name"

    await query.message.reply_text(
        "➕ *አዲስ ምድብ ማስገባት*\n\n"
        "📝 የምድቡን ስም ያስገቡ:",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("❌ ሰርዝ", callback_data="admin_categories")]
        ]),
    )


async def start_edit_category(
    update: Update, context: ContextTypes.DEFAULT_TYPE, cat_id: int
) -> None:
    """Begin edit-category text flow for a specific category."""
    query = update.callback_query
    context.user_data["admin_state"] = "edit_category_name"
    context.user_data["admin_cat_id"] = cat_id

    await query.message.reply_text(
        f"✏️ *ምድብ ማርትዕ* (ID: {cat_id})\n\n"
        "📝 አዲሱን ስም ያስገቡ:",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("❌ ሰርዝ", callback_data="admin_categories")]
        ]),
    )


async def confirm_delete_category(
    update: Update, context: ContextTypes.DEFAULT_TYPE, cat_id: int
) -> None:
    """Show delete-category confirmation panel."""
    query = update.callback_query

    await query.message.edit_text(
        f"🗑️ *ምድቡን ለመሰረዝ እርግጠኛ ነዎት?* (ID: {cat_id})\n\n"
        "⚠️ ይህ ድርጊት ሊቀለበስ አይችልም!",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup([
            [
                InlineKeyboardButton("✅ አዎ፣ ሰርዝ",  callback_data=f"admin_cat_del_confirm_{cat_id}"),
                InlineKeyboardButton("❌ አይ",         callback_data="admin_categories"),
            ]
        ]),
    )


async def do_delete_category(
    update: Update, context: ContextTypes.DEFAULT_TYPE, cat_id: int
) -> None:
    """Actually delete a category."""
    query = update.callback_query

    try:
        async for db in get_db_session():
            cat_service = CategoryService(db)
            success = await cat_service.delete_category(cat_id)
            break

        if success:
            await query.message.edit_text(
                f"✅ ምድቡ (ID: {cat_id}) ተሰርዟል።",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔙 ወደ ምድቦች", callback_data="admin_categories")]
                ]),
            )
        else:
            await query.message.edit_text(
                f"❌ ምድቡ (ID: {cat_id}) አልተገኘም።",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔙 ወደ ምድቦች", callback_data="admin_categories")]
                ]),
            )
    except Exception as exc:
        logger.error("Delete category %s error: %s", cat_id, exc)
        await query.message.edit_text(
            "❌ ምድቡን ለመሰረዝ ስህተት ተፈጥሯል።",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 ወደ ምድቦች", callback_data="admin_categories")]
            ]),
        )


async def do_approve_product(
    update: Update, context: ContextTypes.DEFAULT_TYPE, product_id: int
) -> None:
    """Approve a pending product."""
    query = update.callback_query

    try:
        async for db in get_db_session():
            product_service = ProductService(db)
            await product_service.product_repo.update(product_id, {"status": "active"})
            break
        await query.message.edit_text(
            f"✅ ምርቱ (ID: {product_id}) ፀድቋል!",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 ወደ ምርቶች", callback_data="admin_pending_products")]
            ]),
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
        async for db in get_db_session():
            product_service = ProductService(db)
            await product_service.product_repo.update(product_id, {"status": "rejected"})
            break
        await query.message.edit_text(
            f"❌ ምርቱ (ID: {product_id}) ውድቅ ሆኗል።",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 ወደ ምርቶች", callback_data="admin_pending_products")]
            ]),
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
    """Final step: create product after admin picks a category via inline button."""
    query = update.callback_query

    name  = context.user_data.pop("new_product_name", None)
    price = context.user_data.pop("new_product_price", None)
    stock = context.user_data.pop("new_product_stock", None)

    if not name or price is None or stock is None:
        await query.message.edit_text(
            "❌ ምርቱን ለመፍጠር ያስፈለጉ ዝርዝሮች ጠፍተዋል። እባክዎ ዳግም ይሞክሩ።",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 ወደ ምርቶች", callback_data="admin_products")]
            ]),
        )
        return

    # Use admin's Telegram ID to find (or approximate) a vendor record
    admin_tg_id = update.effective_user.id
    cat_id = category_id if category_id > 0 else None

    # Auto-generate a SKU from the product name
    import re
    import uuid
    sku_base = re.sub(r"[^A-Za-z0-9]", "", name.upper())[:8] or "PROD"
    sku = f"{sku_base}-{uuid.uuid4().hex[:6].upper()}"

    try:
        async for db in get_db_session():
            from apps.users.services import UserService
            user_service = UserService(db)
            admin_user = await user_service.get_user_by_telegram(admin_tg_id)
            vendor_id = admin_user.id if admin_user else 1

            product_service = ProductService(db)
            product = await product_service.create_product(
                vendor_id=vendor_id,
                data=ProductCreate(
                    name=name,
                    price=price,
                    stock_quantity=stock,
                    category_id=cat_id,
                    sku=sku,
                ),
            )
            break

        await query.message.edit_text(
            f"✅ *ምርቱ ተፈጠረ!*\n\n"
            f"• ስም: *{product.name}*\n"
            f"• ዋጋ: {format_etb(product.price)}\n"
            f"• ክምችት: {product.stock_quantity}\n"
            f"• ID: {product.id}",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("📋 ምርቶችን ይዩ", callback_data="admin_list_products")],
                [InlineKeyboardButton("🔙 ወደ ምርት አስተዳደር", callback_data="admin_products")],
            ]),
        )
    except Exception as exc:
        logger.error("Create product error: %s", exc)
        await query.message.edit_text(
            "❌ ምርቱን ለመፍጠር ስህተት ተፈጥሯል። ሻጭ ID ያረጋግጡ።",
            reply_markup=_products_back_keyboard(),
        )


# ── legacy stub (dispatcher.py registers product_admin_callback for ^prod_admin_) ──

async def product_admin_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Legacy entry — all admin_ routing done in dashboard.admin_callback."""
    pass


__all__ = [
    "products_admin_panel",
    "list_products",
    "list_pending_products",
    "manage_categories",
    "start_add_product",
    "start_add_category",
    "start_edit_category",
    "confirm_delete_category",
    "do_delete_category",
    "do_approve_product",
    "do_reject_product",
    "do_create_product_with_category",
    "product_admin_callback",
]
