"""Vendor dashboard handlers for Telegram."""

from decimal import Decimal, InvalidOperation
import re
import uuid

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from core.logger import logger
from core.utils.currency import format_etb
from apps.users.services import UserService, VendorService
from apps.users.schemas import VendorUpdate
from apps.products.services import ProductService
from apps.products.schemas import ProductCreate, ProductUpdate
from apps.orders.services import OrderService
from apps.orders.schemas import OrderStatusUpdate
from infrastructure.database.session import get_db_session


def _back() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("🔙 ወደ የሻጭ ፓነል", callback_data="profile_vendor_panel")
    ]])


async def _vendor_for(update: Update, context: ContextTypes.DEFAULT_TYPE):
    async for db in get_db_session():
        user = await UserService(db).get_user_by_telegram(update.effective_user.id)
        vendor = await VendorService(db).get_vendor_by_user(user.id) if user else None
        break
    if not vendor or not vendor.is_approved:
        await update.effective_message.reply_text(
            "❌ የሻጭ መለያዎ ገና አልጸደቀም።", reply_markup=_back()
        )
        return None
    return vendor


async def vendor_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    action = query.data
    vendor = await _vendor_for(update, context)
    if not vendor:
        return

    if action == "vendor_products":
        context.user_data["vendor_products_page"] = 1
        await list_vendor_products(update, context)
    elif action == "vendor_add_product":
        context.user_data["vendor_state"] = "name"
        await query.message.edit_text(
            "➕ *አዲስ ምርት*\n\nየምርቱን ስም ይላኩ።", parse_mode="Markdown",
            reply_markup=_back()
        )
    elif action == "vendor_orders":
        context.user_data["vendor_orders_page"] = 1
        await list_vendor_orders(update, context)
    elif action == "vendor_stats":
        await show_vendor_stats(update, context, vendor)
    elif action == "vendor_settings":
        context.user_data["vendor_state"] = "business_name"
        await query.message.edit_text(
            f"⚙️ *የንግድ ስም ለመቀየር*\n\nአሁን: *{vendor.business_name}*\n\n"
            "አዲሱን የንግድ ስም ይላኩ።", parse_mode="Markdown", reply_markup=_back()
        )
    elif action.startswith("vendor_edit_"):
        await edit_product_menu(update, context, int(action.rsplit("_", 1)[1]))
    elif action.startswith("vendor_price_"):
        context.user_data["vendor_state"] = "edit_price"
        context.user_data["vendor_product_id"] = int(action.rsplit("_", 1)[1])
        await query.message.edit_text("💰 አዲሱን ዋጋ ይላኩ።", reply_markup=_back())
    elif action.startswith("vendor_stock_"):
        context.user_data["vendor_state"] = "edit_stock"
        context.user_data["vendor_product_id"] = int(action.rsplit("_", 1)[1])
        await query.message.edit_text("📦 አዲሱን stock ቁጥር ይላኩ።", reply_markup=_back())
    elif action.startswith("vendor_delete_"):
        product_id = int(action.rsplit("_", 1)[1])
        async for db in get_db_session():
            ok = await ProductService(db).delete_product(product_id, vendor.id)
            break
        await query.message.edit_text(
            "✅ ምርቱ ተሰርዟል።" if ok else "❌ ምርቱን ማጥፋት አልተቻለም።",
            reply_markup=_back()
        )
    elif action == "vendor_products_next":
        context.user_data["vendor_products_page"] = context.user_data.get("vendor_products_page", 1) + 1
        await list_vendor_products(update, context)
    elif action == "vendor_products_prev":
        context.user_data["vendor_products_page"] = max(1, context.user_data.get("vendor_products_page", 1) - 1)
        await list_vendor_products(update, context)
    elif action == "vendor_orders_next":
        context.user_data["vendor_orders_page"] = context.user_data.get("vendor_orders_page", 1) + 1
        await list_vendor_orders(update, context)
    elif action == "vendor_orders_prev":
        context.user_data["vendor_orders_page"] = max(1, context.user_data.get("vendor_orders_page", 1) - 1)
        await list_vendor_orders(update, context)
    elif action.startswith("vendor_order_"):
        await show_vendor_order(update, context, int(action.rsplit("_", 1)[1]))
    elif action.startswith("vendor_status_"):
        parts = action.split("_")
        order_id, status = int(parts[2]), "_".join(parts[3:])
        async for db in get_db_session():
            order = await OrderService(db).get_order(order_id)
            if not order or order.vendor_id != vendor.id:
                await query.message.edit_text("❌ ይህ ትዕዛዝ የእርስዎ አይደለም።", reply_markup=_back())
                break
            await OrderService(db).update_vendor_order_status(
                order_id, vendor.id, OrderStatusUpdate(status=status), update.effective_user.id
            )
            await query.message.edit_text("✅ የትዕዛዙ ሁኔታ ተቀይሯል።", reply_markup=_back())
            break


async def list_vendor_products(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    vendor = await _vendor_for(update, context)
    if not vendor:
        return
    page = context.user_data.get("vendor_products_page", 1)
    async for db in get_db_session():
        products = await ProductService(db).get_vendor_products(vendor.id, limit=8, offset=(page - 1) * 8)
        break
    text = f"📦 *ምርቶቼ* — ገጽ {page}\n\n"
    keyboard = []
    for product in products:
        text += f"• *{product.name}* — {format_etb(product.price)} | stock: {product.stock_quantity}\n"
        keyboard.append([InlineKeyboardButton(f"✏️ {product.name[:25]}", callback_data=f"vendor_edit_{product.id}")])
    if not products:
        text += "ምንም ምርት አልተገኘም።\n"
    nav = []
    if page > 1:
        nav.append(InlineKeyboardButton("◀️", callback_data="vendor_products_prev"))
    if len(products) == 8:
        nav.append(InlineKeyboardButton("▶️", callback_data="vendor_products_next"))
    if nav:
        keyboard.append(nav)
    keyboard.append([InlineKeyboardButton("➕ አዲስ ምርት", callback_data="vendor_add_product")])
    keyboard.append([InlineKeyboardButton("🔙 ወደ ፓነል", callback_data="profile_vendor_panel")])
    await update.effective_message.edit_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))


async def edit_product_menu(update: Update, context: ContextTypes.DEFAULT_TYPE, product_id: int) -> None:
    vendor = await _vendor_for(update, context)
    if not vendor:
        return
    async for db in get_db_session():
        product = await ProductService(db).get_product(product_id)
        break
    if not product or product.vendor_id != vendor.id:
        await update.effective_message.edit_text("❌ ምርቱ አልተገኘም።", reply_markup=_back())
        return
    keyboard = [
        [InlineKeyboardButton("💰 ዋጋ ቀይር", callback_data=f"vendor_price_{product_id}"),
         InlineKeyboardButton("📦 stock ቀይር", callback_data=f"vendor_stock_{product_id}")],
        [InlineKeyboardButton("🗑️ ምርቱን አጥፋ", callback_data=f"vendor_delete_{product_id}")],
        [InlineKeyboardButton("🔙 ወደ ምርቶቼ", callback_data="vendor_products")],
    ]
    await update.effective_message.edit_text(
        f"✏️ *{product.name}*\n\nዋጋ: {format_etb(product.price)}\nstock: {product.stock_quantity}",
        parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def list_vendor_orders(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    vendor = await _vendor_for(update, context)
    if not vendor:
        return
    page = context.user_data.get("vendor_orders_page", 1)
    async for db in get_db_session():
        orders, total = await OrderService(db).get_vendor_orders(vendor.id, limit=6, offset=(page - 1) * 6)
        break
    text = f"📋 *የሻጭ ትዕዛዞች* — {total}\n\n"
    keyboard = []
    for order in orders:
        text += f"• #{order.order_number} — {format_etb(order.total)} — {order.status}\n"
        keyboard.append([InlineKeyboardButton(f"🔍 #{order.order_number}", callback_data=f"vendor_order_{order.id}")])
    if not orders:
        text += "ምንም ትዕዛዝ የለም።"
    nav = []
    if page > 1:
        nav.append(InlineKeyboardButton("◀️", callback_data="vendor_orders_prev"))
    if page * 6 < total:
        nav.append(InlineKeyboardButton("▶️", callback_data="vendor_orders_next"))
    if nav:
        keyboard.append(nav)
    keyboard.append([InlineKeyboardButton("🔙 ወደ ፓነል", callback_data="profile_vendor_panel")])
    await update.effective_message.edit_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))


async def show_vendor_order(update: Update, context: ContextTypes.DEFAULT_TYPE, order_id: int) -> None:
    vendor = await _vendor_for(update, context)
    if not vendor:
        return
    async for db in get_db_session():
        order = await OrderService(db).get_order(order_id)
        items = await OrderService(db).order_item_repo.get_by_order(order_id)
        break
    vendor_items = [item for item in items if item.vendor_id == vendor.id]
    if not order or (order.vendor_id != vendor.id and not vendor_items):
        await update.effective_message.edit_text("❌ ትዕዛዙ አልተገኘም።", reply_markup=_back())
        return
    vendor_total = sum((item.total_price for item in vendor_items), Decimal("0"))
    vendor_status = vendor_items[0].vendor_status if vendor_items else order.status
    keyboard = [[
        InlineKeyboardButton("✅ Confirm", callback_data=f"vendor_status_{order_id}_confirmed"),
        InlineKeyboardButton("🔄 Processing", callback_data=f"vendor_status_{order_id}_processing"),
    ], [
        InlineKeyboardButton("🚚 Shipped", callback_data=f"vendor_status_{order_id}_shipped"),
        InlineKeyboardButton("🔙 Back", callback_data="vendor_orders"),
    ]]
    await update.effective_message.edit_text(
        f"📋 *ትዕዛዝ #{order.order_number}*\n\n💰 {format_etb(vendor_total)}\n"
        f"📍 {order.shipping_address}, {order.shipping_city}\nሁኔታ: {vendor_status}",
        parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def show_vendor_stats(update: Update, context: ContextTypes.DEFAULT_TYPE, vendor) -> None:
    async for db in get_db_session():
        stats = await VendorService(db).get_vendor_stats(vendor.id)
        break
    await update.effective_message.edit_text(
        f"📊 *{vendor.business_name} — ስታቲስቲክስ*\n\n"
        f"📦 ጠቅላላ ምርቶች: {stats['total_products']}\n"
        f"✅ ንቁ ምርቶች: {stats['active_products']}\n"
        f"🛒 ትዕዛዞች: {stats['total_orders']}\n"
        f"💰 ገቢ: {format_etb(stats['total_revenue'])}\n"
        f"⏳ በመጠባበቅ: {stats['pending_orders']}",
        parse_mode="Markdown", reply_markup=_back()
    )


async def vendor_text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    state = context.user_data.get("vendor_state")
    if not state:
        return
    value = (update.effective_message.text or "").strip()
    if not value:
        return
    if state == "name":
        context.user_data.update(vendor_state="price", vendor_new_name=value)
        await update.effective_message.reply_text("💰 ዋጋውን ይላኩ።")
    elif state == "price":
        try:
            price = Decimal(value.replace(",", ""))
            if price < 0:
                raise InvalidOperation
        except InvalidOperation:
            await update.effective_message.reply_text("❌ ዋጋው ልክ አይደለም።")
            return
        context.user_data.update(vendor_state="stock", vendor_new_price=str(price))
        await update.effective_message.reply_text("📦 stock ቁጥሩን ይላኩ።")
    elif state == "stock":
        if not value.isdigit():
            await update.effective_message.reply_text("❌ stock ሙሉ ቁጥር መሆን አለበት።")
            return
        vendor = await _vendor_for(update, context)
        if not vendor:
            return
        name = context.user_data.pop("vendor_new_name")
        price = Decimal(context.user_data.pop("vendor_new_price"))
        context.user_data.pop("vendor_state", None)
        sku = f"{re.sub(r'[^A-Z0-9]', '', name.upper())[:8] or 'PROD'}-{uuid.uuid4().hex[:8].upper()}"
        async for db in get_db_session():
            product = await ProductService(db).create_product(
                vendor.id, ProductCreate(name=name, price=price, stock_quantity=int(value), sku=sku)
            )
            break
        await update.effective_message.reply_text(f"✅ *{product.name}* ተፈጥሯል።", parse_mode="Markdown", reply_markup=_back())
    elif state in ("edit_price", "edit_stock"):
        product_id = context.user_data.pop("vendor_product_id")
        vendor = await _vendor_for(update, context)
        if not vendor:
            return
        try:
            data = ProductUpdate(price=Decimal(value)) if state == "edit_price" else ProductUpdate(stock_quantity=int(value))
            if state == "edit_stock" and int(value) < 0:
                raise ValueError
        except (ValueError, InvalidOperation):
            await update.effective_message.reply_text("❌ ያስገቡት ዋጋ ልክ አይደለም።")
            context.user_data["vendor_product_id"] = product_id
            return
        context.user_data.pop("vendor_state", None)
        async for db in get_db_session():
            await ProductService(db).update_product(product_id, vendor.id, data)
            break
        await update.effective_message.reply_text("✅ ምርቱ ተስተካክሏል።", reply_markup=_back())
    elif state == "business_name":
        vendor = await _vendor_for(update, context)
        if vendor:
            async for db in get_db_session():
                await VendorService(db).update_vendor(
                    vendor.id, VendorUpdate(business_name=value)
                )
                break
        context.user_data.pop("vendor_state", None)
        await update.effective_message.reply_text("✅ የንግድ ስሙ ተቀይሯል።", reply_markup=_back())


__all__ = ["vendor_callback", "vendor_text_handler"]