# ============================
# WOLLOYEWA STORE BOT - FASTAPI DEPENDENCIES
# ============================
"""FastAPI dependency injection for authentication, database, and common utilities."""

from typing import Optional, AsyncGenerator, Dict, Any
from fastapi import Depends, Header, HTTPException, Request, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from core.config import settings
from core.security import verify_token, verify_telegram_webhook
from core.logger import logger, LoggerContext, request_id_var
from core.exceptions import AuthenticationError, PermissionError, RateLimitError
from infrastructure.database.session import get_db_session
from infrastructure.redis.client import get_redis_client, RedisClient
from sqlalchemy.ext.asyncio import AsyncSession


# ============================
# Security Dependencies
# ============================

security = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: AsyncSession = Depends(get_db_session),
) -> Optional[Dict[str, Any]]:
    """
    Extract and validate JWT token to get current user.
    
    Args:
        credentials: HTTP Bearer token credentials
        db: Database session
        
    Returns:
        Current user data if authenticated
        
    Raises:
        AuthenticationError: If token is invalid or missing
    """
    if not credentials:
        raise AuthenticationError("Authentication required")
    
    token = credentials.credentials
    payload = verify_token(token)
    
    if not payload:
        raise AuthenticationError("Invalid or expired token")
    
    user_id = payload.get("sub")
    if not user_id:
        raise AuthenticationError("Invalid token payload")
    
    # Fetch user from database
    from apps.users.repository import UserRepository
    user_repo = UserRepository(db)
    user = await user_repo.get_by_id(int(user_id))
    
    if not user:
        raise AuthenticationError("User not found")
    
    if user.status != "active":
        raise AuthenticationError("User account is not active")
    
    return {
        "id": user.id,
        "telegram_id": user.telegram_id,
        "role": user.role,
        "username": user.username,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "email": user.email,
        "phone_number": user.phone_number,
        "status": user.status,
    }


async def get_current_admin(
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> Dict[str, Any]:
    """
    Require admin role for access.
    
    Args:
        current_user: Current authenticated user
        
    Returns:
        Current user data if admin
        
    Raises:
        PermissionError: If user is not an admin
    """
    if current_user["role"] not in ["admin", "super_admin"]:
        raise PermissionError("Admin access required")
    return current_user


async def get_current_super_admin(
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> Dict[str, Any]:
    """
    Require super admin role for access.
    
    Args:
        current_user: Current authenticated user
        
    Returns:
        Current user data if super admin
        
    Raises:
        PermissionError: If user is not a super admin
    """
    if current_user["role"] != "super_admin":
        raise PermissionError("Super admin access required")
    return current_user


async def get_current_vendor(
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> Dict[str, Any]:
    """
    Require vendor role or admin for access.
    
    Args:
        current_user: Current authenticated user
        db: Database session
        
    Returns:
        Current user data with vendor info if vendor or admin
        
    Raises:
        PermissionError: If user is not a vendor or admin
    """
    if current_user["role"] not in ["vendor", "admin", "super_admin"]:
        raise PermissionError("Vendor access required")
    
    # If user is vendor, fetch vendor details
    if current_user["role"] == "vendor":
        from apps.users.repository import VendorRepository
        vendor_repo = VendorRepository(db)
        vendor = await vendor_repo.get_by_user_id(current_user["id"])
        if not vendor:
            raise PermissionError("Vendor profile not found")
        current_user["vendor_id"] = vendor.id
        current_user["business_name"] = vendor.business_name
    
    return current_user


# ============================
# Optional Authentication
# ============================

async def get_optional_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: AsyncSession = Depends(get_db_session),
) -> Optional[Dict[str, Any]]:
    """
    Get current user if authenticated, otherwise return None.
    
    Args:
        credentials: Optional HTTP Bearer token credentials
        db: Database session
        
    Returns:
        User data if authenticated, None otherwise
    """
    if not credentials:
        return None
    
    try:
        return await get_current_user(credentials, db)
    except AuthenticationError:
        return None


# ============================
# Request Context Dependencies
# ============================

async def get_request_id(
    x_request_id: Optional[str] = Header(None),
) -> str:
    """
    Get or generate request ID for tracing.
    
    Args:
        x_request_id: Optional request ID from header
        
    Returns:
        Request ID string
    """
    if x_request_id:
        return x_request_id
    import uuid
    return str(uuid.uuid4())


async def get_logger_context(
    request: Request,
    request_id: str = Depends(get_request_id),
    current_user: Optional[Dict[str, Any]] = Depends(get_optional_user),
) -> AsyncGenerator[LoggerContext, None]:
    """
    Setup logging context for the current request.
    
    Args:
        request: FastAPI request object
        request_id: Request ID for tracing
        current_user: Optional authenticated user
        
    Yields:
        LoggerContext for the request
    """
    context = LoggerContext(
        request_id=request_id,
        user_id=current_user.get("id") if current_user else None,
        telegram_id=current_user.get("telegram_id") if current_user else None,
    )
    
    # Store request ID in context var
    request_id_var.set(request_id)
    
    async with context:
        yield context


# ============================
# Rate Limiting Dependency
# ============================

async def check_rate_limit(
    request: Request,
    redis: RedisClient = Depends(get_redis_client),
    key_prefix: str = "rate_limit",
    limit: int = 60,
    window: int = 60,
) -> None:
    """
    Check if request is within rate limits.
    
    Args:
        request: FastAPI request object
        redis: Redis client
        key_prefix: Prefix for rate limit key
        limit: Maximum requests allowed
        window: Time window in seconds
        
    Raises:
        RateLimitError: If rate limit is exceeded
    """
    if not settings.RATE_LIMIT_ENABLED:
        return
    
    # Get client identifier (IP or user ID)
    client_id = request.client.host
    if hasattr(request, "state") and hasattr(request.state, "user_id"):
        client_id = f"user_{request.state.user_id}"
    
    key = f"{key_prefix}:{client_id}"
    
    # Use Redis for rate limiting
    current = await redis.incr(key)
    if current == 1:
        await redis.expire(key, window)
    
    if current > limit:
        raise RateLimitError(retry_after=window)


# ============================
# Pagination Dependencies
# ============================

async def get_pagination_params(
    page: int = 1,
    page_size: int = 20,
) -> Dict[str, int]:
    """
    Extract and validate pagination parameters.
    
    Args:
        page: Page number (starts at 1)
        page_size: Number of items per page
        
    Returns:
        Dictionary with validated pagination parameters
    """
    from core.constants import DEFAULT_PAGE_SIZE, MAX_PAGE_SIZE
    
    if page < 1:
        page = 1
    
    if page_size < 1:
        page_size = DEFAULT_PAGE_SIZE
    elif page_size > MAX_PAGE_SIZE:
        page_size = MAX_PAGE_SIZE
    
    return {
        "page": page,
        "page_size": page_size,
        "offset": (page - 1) * page_size,
        "limit": page_size,
    }


# ============================
# Webhook Verification
# ============================

async def verify_webhook_signature(
    request: Request,
    x_webhook_signature: Optional[str] = Header(None),
) -> None:
    """
    Verify webhook signature for payment callbacks.
    
    Args:
        request: FastAPI request object
        x_webhook_signature: Webhook signature from header
        
    Raises:
        AuthenticationError: If signature verification fails
    """
    if settings.ENVIRONMENT == "development" and settings.DEV_SKIP_MIDDLEWARES:
        return
    
    if not x_webhook_signature:
        raise AuthenticationError("Webhook signature missing")
    
    # Get request body
    body = await request.body()
    
    # Verify signature (implementation depends on payment provider)
    # This is a placeholder - actual verification depends on the provider
    expected_signature = "expected_signature"
    
    if not verify_telegram_webhook({"secret_token": x_webhook_signature}, expected_signature):
        raise AuthenticationError("Invalid webhook signature")


# ============================
# Database Transaction Dependency
# ============================

async def get_transaction_session(
    db: AsyncSession = Depends(get_db_session),
) -> AsyncGenerator[AsyncSession, None]:
    """
    Get database session with transaction management.
    
    Args:
        db: Database session
        
    Yields:
        Database session with transaction
    """
    try:
        yield db
        await db.commit()
    except Exception:
        await db.rollback()
        raise
    finally:
        await db.close()


# ============================
# Export all dependencies
# ============================

__all__ = [
    "get_current_user",
    "get_current_admin",
    "get_current_super_admin",
    "get_current_vendor",
    "get_optional_user",
    "get_request_id",
    "get_logger_context",
    "check_rate_limit",
    "get_pagination_params",
    "verify_webhook_signature",
    "get_transaction_session",
    "get_db_session",
    "get_redis_client",
]