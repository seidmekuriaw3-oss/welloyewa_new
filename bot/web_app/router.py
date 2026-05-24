# ============================
# WOLLOYEWA STORE BOT - WEB APP ROUTER
# ============================
"""FastAPI router for the Telegram Mini App web interface."""

from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from pathlib import Path

from core.config import settings
from core.dependencies import get_current_user, get_db_session
from apps.products.services import ProductService
from apps.orders.services import OrderService
from apps.users.services import UserService

# Setup templates
templates_dir = Path(__file__).parent / "templates"
templates = Jinja2Templates(directory=templates_dir)

web_app_router = APIRouter(prefix="/app", tags=["Web App"])


@web_app_router.get("/", response_class=HTMLResponse)
async def index_page(request: Request):
    """
    Main web app index page.
    """
    return templates.TemplateResponse(
        "index.html",
        {"request": request, "project_name": settings.PROJECT_NAME}
    )


@web_app_router.get("/product/{product_id}", response_class=HTMLResponse)
async def product_page(request: Request, product_id: int):
    """
    Product detail page.
    """
    return templates.TemplateResponse(
        "product.html",
        {"request": request, "product_id": product_id}
    )


@web_app_router.get("/cart", response_class=HTMLResponse)
async def cart_page(request: Request):
    """
    Shopping cart page.
    """
    return templates.TemplateResponse(
        "cart.html",
        {"request": request}
    )


@web_app_router.get("/checkout", response_class=HTMLResponse)
async def checkout_page(request: Request):
    """
    Checkout page.
    """
    return templates.TemplateResponse(
        "checkout.html",
        {"request": request}
    )


# API endpoints for the web app
@web_app_router.get("/api/products")
async def get_products(
    page: int = 1,
    page_size: int = 20,
    db=Depends(get_db_session),
):
    """Get products for web app."""
    product_service = ProductService(db)
    products, total = await product_service.product_repo.get_all_with_count(
        limit=page_size,
        offset=(page - 1) * page_size,
    )
    
    return {
        "items": [p.to_dict() for p in products],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@web_app_router.get("/api/product/{product_id}")
async def get_product(product_id: int, db=Depends(get_db_session)):
    """Get single product."""
    product_service = ProductService(db)
    product = await product_service.get_product(product_id)
    
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    return product.to_dict()


@web_app_router.get("/api/orders")
async def get_orders(
    current_user=Depends(get_current_user),
    db=Depends(get_db_session),
):
    """Get user orders."""
    order_service = OrderService(db)
    orders, total = await order_service.get_user_orders(current_user["id"])
    
    return {
        "items": [o.to_dict() for o in orders],
        "total": total,
    }


@web_app_router.get("/api/user/profile")
async def get_user_profile(
    current_user=Depends(get_current_user),
    db=Depends(get_db_session),
):
    """Get user profile."""
    user_service = UserService(db)
    user = await user_service.get_user(current_user["id"])
    
    return user.to_dict()


__all__ = ["web_app_router"]