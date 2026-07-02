# ============================
# WOLLOYEWA STORE BOT - WEB APP ROUTER
# ============================
"""FastAPI router for the Telegram Mini App web interface."""

import hmac
import hashlib
import json
import urllib.parse
from decimal import Decimal
from typing import List, Optional

from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pathlib import Path
from pydantic import BaseModel

from core.config import settings
from core.logger import logger
from core.dependencies import get_current_user, get_db_session
from apps.products.services import ProductService
from apps.orders.services import OrderService
from apps.users.services import UserService

# Setup templates
templates_dir = Path(__file__).parent / "templates"
templates = Jinja2Templates(directory=str(templates_dir))

web_app_router = APIRouter(prefix="/app", tags=["Web App"])


# ---------------------------------------------------------------------------
# Telegram initData verification
# ---------------------------------------------------------------------------

_INIT_DATA_MAX_AGE_SECONDS = 3600  # reject initData older than 1 hour


def _verify_telegram_init_data(init_data: str, bot_token: str) -> Optional[dict]:
    """
    Verify Telegram Mini App initData using HMAC-SHA256.
    Also validates auth_date freshness (max 1 hour).
    Returns the parsed user dict if valid, None otherwise.
    https://core.telegram.org/bots/webapps#validating-data-received-via-the-mini-app
    """
    import time as _time

    try:
        params = dict(urllib.parse.parse_qsl(init_data, strict_parsing=True))
    except Exception:
        return None

    received_hash = params.pop("hash", None)
    if not received_hash:
        return None

    # Validate auth_date freshness
    auth_date_str = params.get("auth_date")
    if auth_date_str:
        try:
            auth_date = int(auth_date_str)
            if abs(_time.time() - auth_date) > _INIT_DATA_MAX_AGE_SECONDS:
                return None
        except (ValueError, TypeError):
            return None

    data_check_string = "\n".join(f"{k}={v}" for k, v in sorted(params.items()))
    secret_key = hmac.new(b"WebAppData", bot_token.encode(), hashlib.sha256).digest()
    expected_hash = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()

    if not hmac.compare_digest(expected_hash, received_hash):
        return None

    user_str = params.get("user")
    if user_str:
        try:
            return json.loads(user_str)
        except Exception:
            return None
    return {}


# ---------------------------------------------------------------------------
# Checkout request schema
# ---------------------------------------------------------------------------

class CartItemIn(BaseModel):
    id: int
    name: str
    price: float
    qty: int


class CheckoutRequest(BaseModel):
    init_data: Optional[str] = None
    items: List[CartItemIn]
    full_name: str
    phone: str
    city: str
    address: str
    payment_method: str  # "chapa" | "telebirr" | "cbe" | "cod"


_PAYMENT_MAP = {
    "chapa":    "chapa",
    "telebirr": "telebirr",
    "cbe":      "cbe_birr",
    "cod":      "cash_on_delivery",
}

_PAYMENT_LABELS = {
    "chapa":    "🏦 Chapa",
    "telebirr": "📱 Telebirr",
    "cbe":      "🏛️ CBE Birr",
    "cod":      "💵 Cash on Delivery",
}


# ---------------------------------------------------------------------------
# Internal: send Telegram order confirmation
# ---------------------------------------------------------------------------

async def _send_order_confirmation(
    telegram_id: int,
    order_number: str,
    full_name: str,
    city: str,
    total: float,
    items: List[CartItemIn],
    payment_method: str,
) -> None:
    """Fire-and-forget Telegram order confirmation message."""
    from telegram import Bot

    items_text = "\n".join(
        f"  • {i.name} × {i.qty}  —  ETB {i.price * i.qty:,.2f}"
        for i in items
    )
    pm_label = _PAYMENT_LABELS.get(payment_method, payment_method)
    text = (
        f"✅ *Order Confirmed!*\n\n"
        f"📦 Order No: `{order_number}`\n"
        f"👤 Name: {full_name}\n"
        f"📍 Delivery: {city}\n"
        f"💳 Payment: {pm_label}\n\n"
        f"*Items:*\n{items_text}\n\n"
        f"💰 *Total: ETB {total:,.2f}*\n\n"
        f"We'll notify you once your order ships. "
        f"Thank you for shopping at ወሎየዋ ሱቅ! 🇪🇹"
    )
    try:
        async with Bot(token=settings.TELEGRAM_BOT_TOKEN) as bot:
            await bot.send_message(
                chat_id=telegram_id,
                text=text,
                parse_mode="Markdown",
            )
        logger.info(f"Order confirmation sent to Telegram user {telegram_id} for order {order_number}")
    except Exception as exc:
        logger.warning(f"Could not send Telegram confirmation to {telegram_id}: {exc}")


# ---------------------------------------------------------------------------
# Page routes
# ---------------------------------------------------------------------------

_BASE_CTX = {"project_name": settings.PROJECT_NAME}


@web_app_router.get("/", response_class=HTMLResponse)
async def index_page(request: Request):
    return templates.TemplateResponse(request, "index.html", {**_BASE_CTX, "page": "home"})


@web_app_router.get("/categories", response_class=HTMLResponse)
async def categories_page(request: Request):
    return templates.TemplateResponse(request, "categories.html", {**_BASE_CTX, "page": "categories"})


@web_app_router.get("/dashboard", response_class=HTMLResponse)
async def dashboard_page(request: Request):
    return templates.TemplateResponse(request, "dashboard.html", {**_BASE_CTX, "page": "dashboard"})


@web_app_router.get("/product/{product_id}", response_class=HTMLResponse)
async def product_page(request: Request, product_id: int):
    return templates.TemplateResponse(request, "product.html", {**_BASE_CTX, "page": "product", "product_id": product_id})


@web_app_router.get("/cart", response_class=HTMLResponse)
async def cart_page(request: Request):
    return templates.TemplateResponse(request, "cart.html", {**_BASE_CTX, "page": "cart"})


@web_app_router.get("/checkout", response_class=HTMLResponse)
async def checkout_page(request: Request):
    """Checkout page."""
    return templates.TemplateResponse(request, "checkout.html", {**_BASE_CTX, "page": "checkout"})


@web_app_router.get("/orders", response_class=HTMLResponse)
async def orders_page(request: Request):
    return templates.TemplateResponse(request, "orders.html", {**_BASE_CTX, "page": "orders"})


# ---------------------------------------------------------------------------
# JSON API endpoints
# ---------------------------------------------------------------------------

@web_app_router.get("/api/categories")
async def get_categories(db=Depends(get_db_session)):
    """Get categories for web app with live product counts."""
    from sqlalchemy import select, func
    from apps.products.models import Category, Product

    result = await db.execute(
        select(
            Category,
            func.count(Product.id).label("live_count"),
        )
        .outerjoin(Product, (Product.category_id == Category.id) & (Product.is_deleted == False))
        .where(Category.is_active == True)
        .group_by(Category.id)
        .order_by(Category.name)
    )
    rows = result.all()
    return [
        {
            "id": cat.id,
            "name": cat.name,
            "name_am": cat.name_am or "",
            "slug": cat.slug or cat.name,
            "icon_url": getattr(cat, "icon_url", "") or "",
            "image_url": getattr(cat, "image_url", "") or "",
            "product_count": count,
            "is_featured": getattr(cat, "is_featured", False),
        }
        for cat, count in rows
    ]


@web_app_router.get("/api/products")
async def get_products(
    page: int = 1,
    page_size: int = 20,
    q: str = "",
    category_id: Optional[int] = None,
    db=Depends(get_db_session),
):
    """Get products for web app with optional search and category filter."""
    from sqlalchemy import select, or_, func
    from apps.products.models import Product
    from core.constants import ProductStatus
    from fastapi.responses import JSONResponse

    q = q.strip()
    conditions = [Product.is_deleted == False]

    if q:
        pattern = f"%{q}%"
        conditions.append(
            or_(
                func.lower(Product.name).like(func.lower(pattern)),
                func.lower(func.coalesce(Product.name_am, "")).like(func.lower(pattern)),
            )
        )
    if category_id is not None:
        conditions.append(Product.category_id == category_id)

    count_stmt = select(func.count()).select_from(Product).where(*conditions)
    total_result = await db.execute(count_stmt)
    total = total_result.scalar() or 0

    stmt = (
        select(Product)
        .where(*conditions)
        .order_by(Product.is_featured.desc(), Product.id)
        .limit(page_size)
        .offset((page - 1) * page_size)
    )
    result = await db.execute(stmt)
    products = result.scalars().all()

    items = [
        {
            "id": p.id,
            "name": p.name,
            "name_am": p.name_am or "",
            "slug": p.slug or "",
            "description": p.description or "",
            "price": float(p.price),
            "compare_price": float(p.compare_price) if p.compare_price else None,
            "stock_quantity": p.stock_quantity,
            "images": p.images or [],
            "status": p.status if isinstance(p.status, str) else str(p.status.value),
            "is_featured": p.is_featured,
            "category_id": p.category_id,
            "category_type": p.category_type or "",
        }
        for p in products
    ]

    return JSONResponse(
        content={"items": items, "total": total, "page": page, "page_size": page_size},
        headers={"Cache-Control": "no-store"},
    )


@web_app_router.get("/api/search")
async def search_products(q: str = "", limit: int = 6, db=Depends(get_db_session)):
    """
    Autocomplete / search endpoint.
    Returns up to `limit` products whose name or Amharic name contains `q` (case-insensitive).
    """
    from sqlalchemy import select, or_, func
    from sqlalchemy.orm import selectinload
    from apps.products.models import Product
    from core.constants import ProductStatus

    q = q.strip()
    if not q:
        return {"items": [], "query": q}

    pattern = f"%{q}%"
    stmt = (
        select(Product)
        .options(selectinload(Product.category_rel))
        .where(
            Product.is_deleted == False,
            Product.status == ProductStatus.ACTIVE,
            or_(
                func.lower(Product.name).like(func.lower(pattern)),
                func.lower(func.coalesce(Product.name_am, "")).like(func.lower(pattern)),
            ),
        )
        .order_by(Product.name)
        .limit(limit)
    )
    result = await db.execute(stmt)
    products = result.scalars().all()

    return {
        "items": [
            {
                "id": p.id,
                "name": p.name,
                "name_am": getattr(p, "name_am", "") or "",
                "price": float(p.price),
                "category": p.category_rel.name if p.category_rel else "",
                "image_url": (p.images[0] if p.images else "") if p.images else "",
            }
            for p in products
        ],
        "query": q,
    }


@web_app_router.get("/api/product/{product_id}")
async def get_product(product_id: int, db=Depends(get_db_session)):
    """Get single product."""
    product_service = ProductService(db)
    product = await product_service.get_product(product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return product.to_dict()


@web_app_router.post("/api/checkout")
async def api_checkout(body: CheckoutRequest, db=Depends(get_db_session)):
    """
    Place an order from the Telegram Mini App.

    Identifies the user via Telegram initData (HMAC-verified), creates
    the order in the database, and sends a confirmation message back to
    the user's Telegram chat.
    """
    from apps.orders.schemas import OrderCreate, OrderItemCreate
    from core.constants import PaymentMethod, ShippingMethod

    if not body.items:
        raise HTTPException(status_code=400, detail="Cart is empty.")

    # ── Identify Telegram user ───────────────────────────────────────────────
    tg_user: Optional[dict] = None
    if body.init_data:
        tg_user = _verify_telegram_init_data(body.init_data, settings.TELEGRAM_BOT_TOKEN)

    user_service = UserService(db)
    db_user = None

    if tg_user and tg_user.get("id"):
        tg_id = int(tg_user["id"])
        db_user = await user_service.get_user_by_telegram(tg_id)
        if not db_user:
            db_user = await user_service.get_or_create_user(
                telegram_id=tg_id,
                first_name=tg_user.get("first_name") or body.full_name,
                username=tg_user.get("username"),
            )

    # Development fallback: use first seeded user so the checkout is testable
    # in the browser without a real Telegram session.
    if not db_user and settings.DEBUG:
        from sqlalchemy import select
        from apps.users.models import User
        result = await db.execute(select(User).limit(1))
        db_user = result.scalar_one_or_none()

    if not db_user:
        raise HTTPException(
            status_code=401,
            detail="Could not identify your account. Please open this store via Telegram.",
        )

    # ── Map payment method ───────────────────────────────────────────────────
    pm_value = _PAYMENT_MAP.get(body.payment_method, "cash_on_delivery")
    try:
        pm = PaymentMethod(pm_value)
    except ValueError:
        pm = PaymentMethod.CASH_ON_DELIVERY

    # ── Calculate shipping fee ───────────────────────────────────────────────
    subtotal = sum(i.price * i.qty for i in body.items)
    shipping_fee = Decimal("0") if subtotal >= 1000 else Decimal("50")

    # ── Build and create order ───────────────────────────────────────────────
    order_data = OrderCreate(
        payment_method=pm,
        shipping_address=body.address,
        shipping_city=body.city,
        shipping_phone=body.phone,
        shipping_method=ShippingMethod.STANDARD,
        shipping_fee=shipping_fee,
        customer_notes=f"Mini App order — Recipient: {body.full_name}",
        items=[OrderItemCreate(product_id=i.id, quantity=i.qty) for i in body.items],
    )

    order_service = OrderService(db)
    try:
        order = await order_service.create_order(db_user.id, order_data)
    except Exception as exc:
        logger.error(f"Order creation failed: {exc}")
        raise HTTPException(status_code=400, detail=str(exc))

    # ── Send Telegram confirmation (non-blocking) ────────────────────────────
    notify_tg_id = tg_user.get("id") if tg_user else None
    if not notify_tg_id and db_user.telegram_id:
        notify_tg_id = db_user.telegram_id

    if notify_tg_id:
        await _send_order_confirmation(
            telegram_id=int(notify_tg_id),
            order_number=order.order_number,
            full_name=body.full_name,
            city=body.city,
            total=float(order.total),
            items=body.items,
            payment_method=body.payment_method,
        )

    return {
        "order_number": order.order_number,
        "order_id": order.id,
        "total": float(order.total),
    }


@web_app_router.post("/api/auth")
async def tg_auth(request: Request, db=Depends(get_db_session)):
    """
    Authenticate a Telegram Mini App user via initData HMAC-SHA256 verification.
    Returns a short-lived JWT access token + basic user info.

    In DEBUG mode with empty initData, falls back to the first DB user so the
    flow is testable directly in the browser without a real Telegram session.
    """
    try:
        body = await request.json()
    except Exception:
        body = {}

    init_data: str = body.get("init_data", "")
    tg_user: Optional[dict] = None

    if init_data:
        tg_user = _verify_telegram_init_data(init_data, settings.TELEGRAM_BOT_TOKEN)
        if tg_user is None:
            raise HTTPException(status_code=401, detail="Invalid Telegram auth data")

    user_service = UserService(db)
    db_user = None

    if tg_user and tg_user.get("id"):
        db_user = await user_service.get_or_create_user(
            telegram_id=int(tg_user["id"]),
            first_name=tg_user.get("first_name") or "User",
            username=tg_user.get("username"),
        )
    elif settings.DEBUG:
        # Dev fallback: use first user in DB (seeded system vendor or real user)
        from sqlalchemy import select
        from apps.users.models import User
        result = await db.execute(select(User).limit(1))
        db_user = result.scalar_one_or_none()

    if not db_user:
        raise HTTPException(
            status_code=401,
            detail="Could not identify your account. Please open the store via Telegram.",
        )

    from core.security import create_access_token
    token = create_access_token({"sub": str(db_user.id), "telegram_id": db_user.telegram_id})

    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "id": db_user.id,
            "first_name": db_user.first_name or "User",
            "last_name": db_user.last_name or "",
            "username": db_user.username or "",
            "telegram_id": db_user.telegram_id,
        },
    }


class MyOrdersRequest(BaseModel):
    init_data: Optional[str] = None


@web_app_router.post("/api/my-orders")
async def api_my_orders(body: MyOrdersRequest, db=Depends(get_db_session)):
    """
    Return order history for the Telegram Mini App user.
    Identifies the user via initData (HMAC-verified), with DEBUG fallback.
    """
    from sqlalchemy import select
    from sqlalchemy.orm import selectinload
    from apps.orders.models import Order
    from apps.users.models import User

    tg_user: Optional[dict] = None
    if body.init_data:
        tg_user = _verify_telegram_init_data(body.init_data, settings.TELEGRAM_BOT_TOKEN)

    db_user = None
    if tg_user and tg_user.get("id"):
        user_service = UserService(db)
        db_user = await user_service.get_user_by_telegram(int(tg_user["id"]))

    if not db_user and settings.DEBUG:
        result = await db.execute(select(User).limit(1))
        db_user = result.scalar_one_or_none()

    if not db_user:
        raise HTTPException(
            status_code=401,
            detail="Could not identify your account. Please open this store via Telegram.",
        )

    result = await db.execute(
        select(Order)
        .where(Order.user_id == db_user.id)
        .options(selectinload(Order.items))
        .order_by(Order.created_at.desc())
        .limit(30)
    )
    orders = result.scalars().all()

    def _serialize(o: Order) -> dict:
        items = []
        for it in (o.items or []):
            name = f"Product #{it.product_id}"
            if hasattr(it, "product_name") and it.product_name:
                name = it.product_name
            elif it.product:
                name = it.product.name
            items.append({
                "product_id":  it.product_id,
                "name":        name,
                "quantity":    it.quantity,
                "unit_price":  float(it.unit_price),
                "total_price": float(it.total_price),
            })
        return {
            "id":               o.id,
            "order_number":     o.order_number,
            "status":           o.status.value if hasattr(o.status, "value") else str(o.status),
            "payment_method":   o.payment_method.value if hasattr(o.payment_method, "value") else str(o.payment_method),
            "payment_status":   o.payment_status.value if hasattr(o.payment_status, "value") else str(o.payment_status),
            "subtotal":         float(o.subtotal),
            "shipping_fee":     float(o.shipping_fee),
            "tax":              float(o.tax),
            "total":            float(o.total),
            "shipping_city":    o.shipping_city,
            "shipping_address": o.shipping_address,
            "shipping_phone":   o.shipping_phone,
            "tracking_number":  o.tracking_number,
            "customer_notes":   o.customer_notes,
            "created_at":       o.created_at.isoformat() if o.created_at else None,
            "items":            items,
        }

    return {"orders": [_serialize(o) for o in orders], "total": len(orders)}


@web_app_router.get("/api/orders")
async def get_orders(
    current_user=Depends(get_current_user),
    db=Depends(get_db_session),
):
    """Get order history for the authenticated user."""
    from sqlalchemy import select
    from sqlalchemy.orm import selectinload
    from apps.orders.models import Order

    result = await db.execute(
        select(Order)
        .where(Order.user_id == current_user["id"])
        .options(selectinload(Order.items))
        .order_by(Order.created_at.desc())
        .limit(50)
    )
    orders = result.scalars().all()

    def _fmt_order(o: "Order") -> dict:
        return {
            "id": o.id,
            "order_number": o.order_number,
            "status": str(o.status.value if hasattr(o.status, "value") else o.status),
            "total": float(o.total),
            "subtotal": float(o.subtotal),
            "shipping_fee": float(o.shipping_fee),
            "payment_method": str(o.payment_method.value if hasattr(o.payment_method, "value") else o.payment_method),
            "payment_status": str(o.payment_status.value if hasattr(o.payment_status, "value") else o.payment_status),
            "shipping_city": o.shipping_city,
            "created_at": o.created_at.isoformat() if o.created_at else None,
            "item_count": len(o.items),
        }

    return {"items": [_fmt_order(o) for o in orders], "total": len(orders)}


@web_app_router.get("/api/user/profile")
async def get_user_profile(
    current_user=Depends(get_current_user),
    db=Depends(get_db_session),
):
    """Get profile for the authenticated user."""
    user_service = UserService(db)
    user = await user_service.get_user(current_user["id"])
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return {
        "id": user.id,
        "first_name": user.first_name,
        "last_name": user.last_name or "",
        "username": user.username or "",
        "telegram_id": user.telegram_id,
        "phone_number": user.phone_number or "",
        "email": user.email or "",
        "language": user.language,
        "city": user.city or "",
        "created_at": user.created_at.isoformat() if user.created_at else None,
    }


__all__ = ["web_app_router"]
