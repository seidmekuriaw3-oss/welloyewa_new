# ============================
# WOLLOYEWA STORE BOT - PRODUCTS API ENDPOINTS
# ============================
"""REST API endpoints for product management."""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from typing import List, Optional

from core.dependencies import get_current_user, get_current_vendor, get_current_admin, get_db_session
from core.exceptions import NotFoundError, ValidationError, PermissionError
from apps.products.services import ProductService, CategoryService, ReviewService
from apps.products.schemas import (
    ProductCreate,
    ProductUpdate,
    ProductResponse,
    ProductListResponse,
    CategoryCreate,
    CategoryUpdate,
    CategoryResponse,
    ReviewCreate,
    ReviewResponse,
    ReviewSummaryResponse,
    ProductSearchParams,
)
from apps.common.schemas import PaginatedResponse, MessageResponse
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter()


# ============================
# Product Endpoints
# ============================

@router.get("/", response_model=PaginatedResponse[ProductResponse])
async def get_products(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    category: Optional[str] = Query(None, description="Filter by category"),
    vendor_id: Optional[int] = Query(None, description="Filter by vendor"),
    min_price: Optional[float] = Query(None, ge=0),
    max_price: Optional[float] = Query(None, ge=0),
    search: Optional[str] = Query(None, description="Search query"),
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


@router.get("/featured", response_model=List[ProductResponse])
async def get_featured_products(
    limit: int = Query(10, ge=1, le=50),
    db: AsyncSession = Depends(get_db_session),
) -> List[ProductResponse]:
    """
    Get featured products.
    """
    product_service = ProductService(db)
    products = await product_service.get_featured_products(limit)
    return [ProductResponse.model_validate(p) for p in products]


@router.get("/new-arrivals", response_model=List[ProductResponse])
async def get_new_arrivals(
    limit: int = Query(10, ge=1, le=50),
    db: AsyncSession = Depends(get_db_session),
) -> List[ProductResponse]:
    """
    Get new arrivals.
    """
    product_service = ProductService(db)
    products = await product_service.get_new_arrivals(limit)
    return [ProductResponse.model_validate(p) for p in products]


@router.get("/on-sale", response_model=List[ProductResponse])
async def get_products_on_sale(
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db_session),
) -> List[ProductResponse]:
    """
    Get products on sale.
    """
    product_service = ProductService(db)
    products = await product_service.get_products_on_sale(limit)
    return [ProductResponse.model_validate(p) for p in products]


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
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


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
    
    try:
        product = await product_service.create_product(current_user["vendor_id"], data)
        return ProductResponse.model_validate(product)
    except ValidationError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))


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
    
    try:
        product = await product_service.update_product(product_id, current_user["vendor_id"], data)
        return ProductResponse.model_validate(product)
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))


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
    
    try:
        await product_service.delete_product(product_id, current_user["vendor_id"])
        return MessageResponse(message=f"Product {product_id} deleted successfully")
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))


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
    
    reviews, total = await review_service.get_product_reviews(product_id, page_size, (page - 1) * page_size)
    
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


@router.post("/{product_id}/reviews", response_model=ReviewResponse, status_code=status.HTTP_201_CREATED)
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
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


# ============================
# Category Endpoints
# ============================

@router.get("/categories", response_model=List[CategoryResponse])
async def get_categories(
    db: AsyncSession = Depends(get_db_session),
) -> List[CategoryResponse]:
    """
    Get all categories.
    """
    category_service = CategoryService(db)
    categories = await category_service.get_all_categories()
    return [CategoryResponse.model_validate(c) for c in categories]


@router.get("/categories/tree", response_model=List[dict])
async def get_category_tree(
    db: AsyncSession = Depends(get_db_session),
) -> List[dict]:
    """
    Get hierarchical category tree.
    """
    category_service = CategoryService(db)
    return await category_service.get_category_tree()


@router.post("/categories", response_model=CategoryResponse, status_code=status.HTTP_201_CREATED)
async def create_category(
    data: CategoryCreate,
    current_user: dict = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db_session),
) -> CategoryResponse:
    """
    Create a new category (admin only).
    """
    category_service = CategoryService(db)
    
    try:
        category = await category_service.create_category(data)
        return CategoryResponse.model_validate(category)
    except ValidationError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))


@router.put("/categories/{category_id}", response_model=CategoryResponse)
async def update_category(
    category_id: int,
    data: CategoryUpdate,
    current_user: dict = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db_session),
) -> CategoryResponse:
    """
    Update a category (admin only).
    """
    category_service = CategoryService(db)
    
    try:
        category = await category_service.update_category(category_id, data)
        return CategoryResponse.model_validate(category)
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.delete("/categories/{category_id}", response_model=MessageResponse)
async def delete_category(
    category_id: int,
    current_user: dict = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db_session),
) -> MessageResponse:
    """
    Delete a category (admin only).
    """
    category_service = CategoryService(db)
    
    try:
        await category_service.delete_category(category_id)
        return MessageResponse(message=f"Category {category_id} deleted successfully")
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


# ============================
# Vendor Product Management
# ============================

@router.get("/vendor/products", response_model=PaginatedResponse[ProductResponse])
async def get_my_products(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: Optional[str] = Query(None, description="Filter by status"),
    current_user: dict = Depends(get_current_vendor),
    db: AsyncSession = Depends(get_db_session),
) -> PaginatedResponse[ProductResponse]:
    """
    Get current vendor's products.
    """
    product_service = ProductService(db)
    
    products = await product_service.get_vendor_products(
        vendor_id=current_user["vendor_id"],
        status=status,
        limit=page_size,
        offset=(page - 1) * page_size,
    )
    total = len(products)  # Would need separate count query
    
    return PaginatedResponse.create(
        items=[ProductResponse.model_validate(p) for p in products],
        total=total,
        page=page,
        page_size=page_size,
    )


__all__ = ["router"]