# ============================
# WOLLOYEWA STORE BOT - PRODUCTS API ENDPOINTS
# ============================
"""REST API endpoints for product management."""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from apps.common.schemas import MessageResponse, PaginatedResponse
from apps.products.schemas import (
    CategoryCreate,
    CategoryResponse,
    CategoryUpdate,
    ProductCreate,
    ProductResponse,
    ProductUpdate,
    ReviewCreate,
    ReviewResponse,
    ReviewSummaryResponse,
)
from apps.products.services import CategoryService, ProductService, ReviewService
from core.dependencies import (
    get_current_admin,
    get_current_user,
    get_current_vendor,
    get_db_session,
)
from core.exceptions import NotFoundError, PermissionError, ValidationError

router = APIRouter()


# ============================
# Product Endpoints
# ============================


@router.get("/", response_model=PaginatedResponse[ProductResponse])
async def get_products(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    category: str | None = Query(None, description="Filter by category"),
    vendor_id: int | None = Query(None, description="Filter by vendor"),
    min_price: float | None = Query(None, ge=0),
    max_price: float | None = Query(None, ge=0),
    search: str | None = Query(None, description="Search query"),
    db: AsyncSession = Depends(get_db_session),
) -> PaginatedResponse[ProductResponse]:
    """
    Get products with pagination and filters.

    Returns a paginated list of products.
    """
    product_service = ProductService(db)

    # Search products if query provided
    if search:
        products = await product_service.search_products(
            query=search,
            category=category,
            min_price=min_price,
            max_price=max_price,
            limit=page_size,
        )
        total = len(products)
    else:
        filters = {}
        if category:
            filters["category"] = category
        if vendor_id:
            filters["vendor_id"] = vendor_id

        products, total = await product_service.product_repo.get_all_with_count(
            filters=filters,
            limit=page_size,
            offset=(page - 1) * page_size,
        )

    return PaginatedResponse.create(
        items=[ProductResponse.model_validate(p) for p in products],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/featured", response_model=list[ProductResponse])
async def get_featured_products(
    limit: int = Query(10, ge=1, le=50),
    db: AsyncSession = Depends(get_db_session),
) -> list[ProductResponse]:
    """
    Get featured products.
    """
    product_service = ProductService(db)
    products = await product_service.get_featured_products(limit)
    return [ProductResponse.model_validate(p) for p in products]


@router.get("/new-arrivals", response_model=list[ProductResponse])
async def get_new_arrivals(
    limit: int = Query(10, ge=1, le=50),
    db: AsyncSession = Depends(get_db_session),
) -> list[ProductResponse]:
    """
    Get new arrivals.
    """
    product_service = ProductService(db)
    products = await product_service.get_new_arrivals(limit)
    return [ProductResponse.model_validate(p) for p in products]


@router.get("/on-sale", response_model=list[ProductResponse])
async def get_products_on_sale(
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db_session),
) -> list[ProductResponse]:
    """
    Get products on sale.
    """
    product_service = ProductService(db)
    products = await product_service.get_products_on_sale(limit)
    return [ProductResponse.model_validate(p) for p in products]


# ============================
# Category Endpoints (must be BEFORE /{product_id} to avoid route shadowing)
# ============================


@router.get("/categories", response_model=list[CategoryResponse])
async def get_categories(
    db: AsyncSession = Depends(get_db_session),
) -> list[CategoryResponse]:
    """Get all categories."""
    category_service = CategoryService(db)
    categories = await category_service.get_all_categories()
    return [CategoryResponse.model_validate(c) for c in categories]


@router.get("/categories/tree", response_model=list[dict])
async def get_category_tree(
    db: AsyncSession = Depends(get_db_session),
) -> list[dict]:
    """Get hierarchical category tree."""
    category_service = CategoryService(db)
    return await category_service.get_category_tree()


@router.post("/categories", response_model=CategoryResponse, status_code=status.HTTP_201_CREATED)
async def create_category(
    data: CategoryCreate,
    current_user: dict = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db_session),
) -> CategoryResponse:
    """Create a new category (admin only)."""
    category_service = CategoryService(db)
    try:
        category = await category_service.create_category(data)
        return CategoryResponse.model_validate(category)
    except ValidationError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e)) from e


@router.put("/categories/{category_id}", response_model=CategoryResponse)
async def update_category(
    category_id: int,
    data: CategoryUpdate,
    current_user: dict = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db_session),
) -> CategoryResponse:
    """Update a category (admin only)."""
    category_service = CategoryService(db)
    try:
        category = await category_service.update_category(category_id, data)
        return CategoryResponse.model_validate(category)
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e


@router.delete("/categories/{category_id}", response_model=MessageResponse)
async def delete_category(
    category_id: int,
    current_user: dict = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db_session),
) -> MessageResponse:
    """Delete a category (admin only)."""
    category_service = CategoryService(db)
    try:
        await category_service.delete_category(category_id)
        return MessageResponse(message=f"Category {category_id} deleted successfully")
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e


# ============================
# Vendor Product Management (must be BEFORE /{product_id})
# ============================


@router.get("/vendor/products", response_model=PaginatedResponse[ProductResponse])
async def get_my_products(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: str | None = Query(None, description="Filter by status"),
    current_user: dict = Depends(get_current_vendor),
    db: AsyncSession = Depends(get_db_session),
) -> PaginatedResponse[ProductResponse]:
    """Get current vendor's products."""
    product_service = ProductService(db)
    if current_user.get("vendor_id"):
        products = await product_service.get_vendor_products(
            vendor_id=current_user["vendor_id"],
            status=status,
            limit=page_size,
            offset=(page - 1) * page_size,
        )
        total = len(products)
    else:
        filters = {"status": status} if status else None
        products, total = await product_service.product_repo.get_all_with_count(
            filters=filters,
            limit=page_size,
            offset=(page - 1) * page_size,
        )
    return PaginatedResponse.create(
        items=[ProductResponse.model_validate(p) for p in products],
        total=total,
        page=page,
        page_size=page_size,
    )


# ============================
# Single Product by ID (dynamic segment — must come LAST)
# ============================


@router.get("/{product_id}", response_model=ProductResponse)
async def get_product(
    product_id: int,
    db: AsyncSession = Depends(get_db_session),
) -> ProductResponse:
    """
    Get product by ID.

    Increments view count automatically.
    """
    product_service = ProductService(db)

    try:
        product = await product_service.get_product(product_id)
        # Increment view count in background
        await product_service.increment_view_count(product_id)
        return ProductResponse.model_validate(product)
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e


@router.post("/", response_model=ProductResponse, status_code=status.HTTP_201_CREATED)
async def create_product(
    data: ProductCreate,
    current_user: dict = Depends(get_current_vendor),
    db: AsyncSession = Depends(get_db_session),
) -> ProductResponse:
    """
    Create a new product (vendor only).
    """
    product_service = ProductService(db)
    vendor_id = current_user.get("vendor_id")
    if not vendor_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Vendor profile required")

    try:
        product = await product_service.create_product(vendor_id, data)
        return ProductResponse.model_validate(product)
    except ValidationError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e)) from e


@router.put("/{product_id}", response_model=ProductResponse)
async def update_product(
    product_id: int,
    data: ProductUpdate,
    current_user: dict = Depends(get_current_vendor),
    db: AsyncSession = Depends(get_db_session),
) -> ProductResponse:
    """
    Update a product (vendor only).
    """
    product_service = ProductService(db)
    vendor_id = current_user.get("vendor_id")
    if not vendor_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Vendor profile required")

    try:
        product = await product_service.update_product(product_id, vendor_id, data)
        return ProductResponse.model_validate(product)
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e)) from e


@router.delete("/{product_id}", response_model=MessageResponse)
async def delete_product(
    product_id: int,
    current_user: dict = Depends(get_current_vendor),
    db: AsyncSession = Depends(get_db_session),
) -> MessageResponse:
    """
    Delete a product (vendor only).
    """
    product_service = ProductService(db)
    vendor_id = current_user.get("vendor_id")
    if not vendor_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Vendor profile required")

    try:
        await product_service.delete_product(product_id, vendor_id)
        return MessageResponse(message=f"Product {product_id} deleted successfully")
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e)) from e


# ============================
# Product Reviews Endpoints
# ============================


@router.get("/{product_id}/reviews", response_model=PaginatedResponse[ReviewResponse])
async def get_product_reviews(
    product_id: int,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=50),
    db: AsyncSession = Depends(get_db_session),
) -> PaginatedResponse[ReviewResponse]:
    """
    Get reviews for a product.
    """
    review_service = ReviewService(db)

    reviews, total = await review_service.get_product_reviews(
        product_id, page_size, (page - 1) * page_size
    )

    return PaginatedResponse.create(
        items=[ReviewResponse.model_validate(r) for r in reviews],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/{product_id}/reviews/summary", response_model=ReviewSummaryResponse)
async def get_product_review_summary(
    product_id: int,
    db: AsyncSession = Depends(get_db_session),
) -> ReviewSummaryResponse:
    """
    Get review summary for a product.
    """
    review_service = ReviewService(db)
    summary = await review_service.get_review_summary(product_id)
    return ReviewSummaryResponse(**summary)


@router.post(
    "/{product_id}/reviews", response_model=ReviewResponse, status_code=status.HTTP_201_CREATED
)
async def create_product_review(
    product_id: int,
    data: ReviewCreate,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> ReviewResponse:
    """
    Create a review for a product.
    """
    review_service = ReviewService(db)

    try:
        review = await review_service.create_review(current_user["id"], product_id, data)
        return ReviewResponse.model_validate(review)
    except (NotFoundError, ValidationError) as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e


__all__ = ["router"]
