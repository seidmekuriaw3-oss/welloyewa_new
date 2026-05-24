# ============================
# WOLLOYEWA STORE BOT - PAGINATION UTILITIES
# ============================
"""Pagination helpers for database queries and API responses."""

import math
from typing import Any, Dict, Generic, List, Optional, TypeVar, Union
from dataclasses import dataclass, field
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

T = TypeVar('T')


@dataclass
class PageInfo:
    """Pagination metadata."""
    
    page: int
    page_size: int
    total_items: int
    total_pages: int
    has_next: bool = False
    has_previous: bool = False
    
    def __post_init__(self):
        self.total_pages = math.ceil(self.total_items / self.page_size) if self.page_size > 0 else 0
        self.has_next = self.page < self.total_pages
        self.has_previous = self.page > 1
    
    @property
    def next_page(self) -> Optional[int]:
        """Return next page number if exists."""
        return self.page + 1 if self.has_next else None
    
    @property
    def previous_page(self) -> Optional[int]:
        """Return previous page number if exists."""
        return self.page - 1 if self.has_previous else None
    
    @property
    def start_item(self) -> int:
        """Return starting item number (1-indexed)."""
        if self.total_items == 0:
            return 0
        return (self.page - 1) * self.page_size + 1
    
    @property
    def end_item(self) -> int:
        """Return ending item number (1-indexed)."""
        if self.total_items == 0:
            return 0
        return min(self.page * self.page_size, self.total_items)


@dataclass
class PaginationResult(Generic[T]):
    """Generic paginated result container."""
    
    items: List[T]
    page_info: PageInfo
    
    def to_dict(self, item_serializer=None) -> Dict[str, Any]:
        """Convert to dictionary for API responses."""
        items_data = (
            [item_serializer(item) for item in self.items]
            if item_serializer
            else [item for item in self.items]
        )
        
        return {
            "items": items_data,
            "pagination": {
                "page": self.page_info.page,
                "page_size": self.page_info.page_size,
                "total_items": self.page_info.total_items,
                "total_pages": self.page_info.total_pages,
                "has_next": self.page_info.has_next,
                "has_previous": self.page_info.has_previous,
                "next_page": self.page_info.next_page,
                "previous_page": self.page_info.previous_page,
                "start_item": self.page_info.start_item,
                "end_item": self.page_info.end_item,
            }
        }


class Paginator:
    """
    Paginator for database queries.
    
    Usage:
        paginator = Paginator(db, User, page=1, page_size=20)
        result = await paginator.paginate()
    """
    
    def __init__(
        self,
        db: AsyncSession,
        model: Any = None,
        query: Any = None,
        page: int = 1,
        page_size: int = 20,
        order_by: Optional[str] = None,
        order_desc: bool = False,
    ):
        self.db = db
        self.model = model
        self.custom_query = query
        self.page = max(1, page)
        self.page_size = min(100, max(1, page_size))
        self.order_by = order_by
        self.order_desc = order_desc
    
    async def paginate(self) -> PaginationResult:
        """Execute paginated query."""
        # Build base query
        if self.custom_query:
            query = self.custom_query
        else:
            query = select(self.model)
        
        # Apply ordering
        if self.order_by:
            order_column = getattr(self.model, self.order_by)
            if self.order_desc:
                query = query.order_by(order_column.desc())
            else:
                query = query.order_by(order_column)
        
        # Get total count
        count_query = select(func.count()).select_from(query.subquery())
        total_items = await self.db.scalar(count_query)
        total_items = total_items or 0
        
        # Apply pagination
        offset = (self.page - 1) * self.page_size
        query = query.offset(offset).limit(self.page_size)
        
        # Execute query
        result = await self.db.execute(query)
        items = result.scalars().all() if self.model else result.all()
        
        # Create page info
        page_info = PageInfo(
            page=self.page,
            page_size=self.page_size,
            total_items=total_items,
        )
        
        return PaginationResult(items=list(items), page_info=page_info)


async def paginate_query(
    db: AsyncSession,
    query: Any,
    page: int = 1,
    page_size: int = 20,
) -> PaginationResult:
    """
    Paginate any SQLAlchemy query.
    
    Args:
        db: Database session
        query: SQLAlchemy query object
        page: Page number (starts at 1)
        page_size: Items per page
        
    Returns:
        PaginationResult containing items and metadata
    """
    page = max(1, page)
    page_size = min(100, max(1, page_size))
    offset = (page - 1) * page_size
    
    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    total_items = await db.scalar(count_query)
    total_items = total_items or 0
    
    # Apply pagination
    paginated_query = query.offset(offset).limit(page_size)
    result = await db.execute(paginated_query)
    
    # Extract items (handle both ORM models and tuples)
    if hasattr(result, 'scalars'):
        items = result.scalars().all()
    else:
        items = result.all()
    
    page_info = PageInfo(
        page=page,
        page_size=page_size,
        total_items=total_items,
    )
    
    return PaginationResult(items=list(items), page_info=page_info)


def paginate_list(
    items: List[T],
    page: int = 1,
    page_size: int = 20,
) -> PaginationResult:
    """
    Paginate an in-memory list.
    
    Args:
        items: List of items to paginate
        page: Page number (starts at 1)
        page_size: Items per page
        
    Returns:
        PaginationResult containing sliced items and metadata
    """
    page = max(1, page)
    page_size = min(100, max(1, page_size))
    
    total_items = len(items)
    start = (page - 1) * page_size
    end = start + page_size
    
    paginated_items = items[start:end]
    
    page_info = PageInfo(
        page=page,
        page_size=page_size,
        total_items=total_items,
    )
    
    return PaginationResult(items=paginated_items, page_info=page_info)


def generate_pagination_links(
    base_url: str,
    page_info: PageInfo,
    query_params: Optional[Dict[str, Any]] = None,
) -> Dict[str, Optional[str]]:
    """
    Generate HATEOAS pagination links for API responses.
    
    Args:
        base_url: Base URL for the endpoint
        page_info: PageInfo object with pagination metadata
        query_params: Additional query parameters to include
        
    Returns:
        Dictionary with self, first, last, next, prev links
    """
    def build_url(page: int) -> str:
        params = {"page": page}
        if query_params:
            params.update(query_params)
        
        param_str = "&".join(f"{k}={v}" for k, v in params.items())
        return f"{base_url}?{param_str}"
    
    links = {
        "self": build_url(page_info.page),
        "first": build_url(1),
        "last": build_url(page_info.total_pages) if page_info.total_pages > 0 else None,
        "next": build_url(page_info.next_page) if page_info.has_next else None,
        "prev": build_url(page_info.previous_page) if page_info.has_previous else None,
    }
    
    return links


class CursorPaginator:
    """
    Cursor-based pagination for infinite scrolling.
    More efficient than offset pagination for large datasets.
    
    Usage:
        paginator = CursorPaginator(db, User, cursor_field="id")
        result = await paginator.paginate(cursor=last_id, limit=20)
    """
    
    def __init__(
        self,
        db: AsyncSession,
        model: Any,
        cursor_field: str = "id",
        limit: int = 20,
        order_desc: bool = True,
    ):
        self.db = db
        self.model = model
        self.cursor_field = cursor_field
        self.limit = min(100, max(1, limit))
        self.order_desc = order_desc
    
    async def paginate(
        self,
        cursor: Optional[Any] = None,
        limit: Optional[int] = None,
    ) -> PaginationResult:
        """Execute cursor-based paginated query."""
        limit = min(100, max(1, limit or self.limit))
        
        # Build query
        query = select(self.model)
        
        # Apply cursor
        if cursor is not None:
            cursor_column = getattr(self.model, self.cursor_field)
            if self.order_desc:
                query = query.where(cursor_column < cursor)
            else:
                query = query.where(cursor_column > cursor)
        
        # Apply ordering
        cursor_column = getattr(self.model, self.cursor_field)
        if self.order_desc:
            query = query.order_by(cursor_column.desc())
        else:
            query = query.order_by(cursor_column)
        
        # Get one extra item to determine if there's a next page
        query = query.limit(limit + 1)
        
        # Execute query
        result = await self.db.execute(query)
        items = result.scalars().all()
        
        # Check if there's a next page
        has_next = len(items) > limit
        items = items[:limit]
        
        # Get next cursor
        next_cursor = None
        if has_next and items:
            last_item = items[-1]
            next_cursor = getattr(last_item, self.cursor_field)
        
        # Create page info (simplified for cursor pagination)
        page_info = PageInfo(
            page=1,  # Not used in cursor pagination
            page_size=len(items),
            total_items=0,  # Not easily available in cursor pagination
            total_pages=0,
        )
        
        result = PaginationResult(items=items, page_info=page_info)
        result.next_cursor = next_cursor
        result.has_next = has_next
        
        return result


__all__ = [
    "PageInfo",
    "PaginationResult",
    "Paginator",
    "paginate_query",
    "paginate_list",
    "generate_pagination_links",
    "CursorPaginator",
]