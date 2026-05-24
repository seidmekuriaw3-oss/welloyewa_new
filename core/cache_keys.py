# ============================
# WOLLOYEWA STORE BOT - CACHE KEYS
# ============================
"""Centralized cache key definitions and management."""

from typing import Any, Dict, List, Optional, Union
from datetime import datetime, timedelta


class CacheTTL:
    """Cache TTL values in seconds."""
    
    # Short-lived caches (seconds)
    SHORT: int = 60  # 1 minute
    VERY_SHORT: int = 30  # 30 seconds
    
    # Medium-lived caches (minutes)
    MEDIUM: int = 300  # 5 minutes
    STANDARD: int = 600  # 10 minutes
    LONG: int = 3600  # 1 hour
    
    # Long-lived caches (hours)
    VERY_LONG: int = 86400  # 24 hours
    EXTRA_LONG: int = 604800  # 7 days
    
    # Permanent/session
    SESSION: int = 86400  # 24 hours
    PERMANENT: int = None  # No expiration
    
    # Dynamic TTLs (based on data type)
    @classmethod
    def for_user(cls, user_id: int = None) -> int:
        """TTL for user data (shorter for active users)."""
        return cls.MEDIUM
    
    @classmethod
    def for_product(cls, product_id: int = None) -> int:
        """TTL for product data."""
        return cls.LONG
    
    @classmethod
    def for_product_list(cls, category: str = None) -> int:
        """TTL for product lists."""
        return cls.MEDIUM
    
    @classmethod
    def for_order(cls, order_id: int = None) -> int:
        """TTL for order data."""
        return cls.STANDARD
    
    @classmethod
    def for_session(cls, session_id: str = None) -> int:
        """TTL for session data."""
        return cls.SESSION
    
    @classmethod
    def for_analytics(cls, report_type: str = None) -> int:
        """TTL for analytics/report data."""
        return cls.VERY_LONG


class CacheKey:
    """
    Centralized cache key generator.
    
    Usage:
        key = CacheKey.user(123)
        key = CacheKey.product_list(category="electronics", page=1)
    """
    
    # ============================
    # User Related Keys
    # ============================
    
    @staticmethod
    def user(user_id: int) -> str:
        """Cache key for user data."""
        return f"user:{user_id}"
    
    @staticmethod
    def user_by_telegram(telegram_id: int) -> str:
        """Cache key for user lookup by Telegram ID."""
        return f"user:telegram:{telegram_id}"
    
    @staticmethod
    def user_by_email(email: str) -> str:
        """Cache key for user lookup by email."""
        return f"user:email:{email.lower()}"
    
    @staticmethod
    def user_by_phone(phone: str) -> str:
        """Cache key for user lookup by phone."""
        return f"user:phone:{phone}"
    
    @staticmethod
    def user_preferences(user_id: int) -> str:
        """Cache key for user preferences."""
        return f"user:{user_id}:preferences"
    
    @staticmethod
    def user_cart(user_id: int) -> str:
        """Cache key for user cart."""
        return f"user:{user_id}:cart"
    
    @staticmethod
    def user_wishlist(user_id: int) -> str:
        """Cache key for user wishlist."""
        return f"user:{user_id}:wishlist"
    
    @staticmethod
    def user_orders(user_id: int, status: str = None) -> str:
        """Cache key for user orders (optionally filtered by status)."""
        if status:
            return f"user:{user_id}:orders:{status}"
        return f"user:{user_id}:orders"
    
    @staticmethod
    def user_addresses(user_id: int) -> str:
        """Cache key for user addresses."""
        return f"user:{user_id}:addresses"
    
    @staticmethod
    def user_notifications(user_id: int, unread_only: bool = False) -> str:
        """Cache key for user notifications."""
        if unread_only:
            return f"user:{user_id}:notifications:unread"
        return f"user:{user_id}:notifications"
    
    @staticmethod
    def user_session(session_id: str) -> str:
        """Cache key for user session."""
        return f"session:{session_id}"
    
    @staticmethod
    def user_otp(identifier: str, purpose: str) -> str:
        """Cache key for OTP verification."""
        return f"otp:{purpose}:{identifier}"
    
    @staticmethod
    def user_rate_limit(user_id: int, action: str) -> str:
        """Cache key for user rate limiting."""
        return f"rate_limit:user:{user_id}:{action}"
    
    # ============================
    # Vendor Related Keys
    # ============================
    
    @staticmethod
    def vendor(vendor_id: int) -> str:
        """Cache key for vendor data."""
        return f"vendor:{vendor_id}"
    
    @staticmethod
    def vendor_by_user(user_id: int) -> str:
        """Cache key for vendor lookup by user ID."""
        return f"vendor:user:{user_id}"
    
    @staticmethod
    def vendor_products(vendor_id: int, status: str = None) -> str:
        """Cache key for vendor products."""
        if status:
            return f"vendor:{vendor_id}:products:{status}"
        return f"vendor:{vendor_id}:products"
    
    @staticmethod
    def vendor_orders(vendor_id: int, status: str = None) -> str:
        """Cache key for vendor orders."""
        if status:
            return f"vendor:{vendor_id}:orders:{status}"
        return f"vendor:{vendor_id}:orders"
    
    @staticmethod
    def vendor_stats(vendor_id: int) -> str:
        """Cache key for vendor statistics."""
        return f"vendor:{vendor_id}:stats"
    
    @staticmethod
    def vendor_earnings(vendor_id: int, period: str = "monthly") -> str:
        """Cache key for vendor earnings."""
        return f"vendor:{vendor_id}:earnings:{period}"
    
    # ============================
    # Product Related Keys
    # ============================
    
    @staticmethod
    def product(product_id: int) -> str:
        """Cache key for individual product."""
        return f"product:{product_id}"
    
    @staticmethod
    def product_by_sku(sku: str) -> str:
        """Cache key for product lookup by SKU."""
        return f"product:sku:{sku}"
    
    @staticmethod
    def product_by_slug(slug: str) -> str:
        """Cache key for product lookup by slug."""
        return f"product:slug:{slug}"
    
    @staticmethod
    def product_list(
        category: str = None,
        vendor_id: int = None,
        sort_by: str = "created_at",
        page: int = 1,
        page_size: int = 20,
    ) -> str:
        """Cache key for product list with filters."""
        parts = ["products"]
        if category:
            parts.append(f"cat:{category}")
        if vendor_id:
            parts.append(f"vendor:{vendor_id}")
        parts.append(f"sort:{sort_by}")
        parts.append(f"p:{page}")
        parts.append(f"ps:{page_size}")
        return ":".join(map(str, parts))
    
    @staticmethod
    def product_reviews(product_id: int, page: int = 1) -> str:
        """Cache key for product reviews."""
        return f"product:{product_id}:reviews:p:{page}"
    
    @staticmethod
    def product_rating(product_id: int) -> str:
        """Cache key for product rating summary."""
        return f"product:{product_id}:rating"
    
    @staticmethod
    def product_stock(product_id: int) -> str:
        """Cache key for product stock level."""
        return f"product:{product_id}:stock"
    
    @staticmethod
    def product_categories() -> str:
        """Cache key for product categories."""
        return "products:categories"
    
    @staticmethod
    def featured_products(limit: int = 10) -> str:
        """Cache key for featured products."""
        return f"products:featured:limit:{limit}"
    
    @staticmethod
    def popular_products(limit: int = 10, period: str = "week") -> str:
        """Cache key for popular products."""
        return f"products:popular:{period}:limit:{limit}"
    
    @staticmethod
    def new_products(limit: int = 10) -> str:
        """Cache key for new products."""
        return f"products:new:limit:{limit}"
    
    @staticmethod
    def discounted_products(limit: int = 10) -> str:
        """Cache key for discounted products."""
        return f"products:discounted:limit:{limit}"
    
    # ============================
    # Order Related Keys
    # ============================
    
    @staticmethod
    def order(order_id: int) -> str:
        """Cache key for individual order."""
        return f"order:{order_id}"
    
    @staticmethod
    def order_by_number(order_number: str) -> str:
        """Cache key for order lookup by order number."""
        return f"order:number:{order_number}"
    
    @staticmethod
    def order_items(order_id: int) -> str:
        """Cache key for order items."""
        return f"order:{order_id}:items"
    
    @staticmethod
    def order_tracking(order_id: int) -> str:
        """Cache key for order tracking info."""
        return f"order:{order_id}:tracking"
    
    @staticmethod
    def order_invoice(order_id: int) -> str:
        """Cache key for order invoice."""
        return f"order:{order_id}:invoice"
    
    # ============================
    # Search Related Keys
    # ============================
    
    @staticmethod
    def search_query(query: str, filters: Dict = None, page: int = 1) -> str:
        """Cache key for search results."""
        import hashlib
        filter_str = str(sorted(filters.items())) if filters else ""
        unique = f"{query}:{filter_str}:{page}"
        hash_key = hashlib.md5(unique.encode()).hexdigest()
        return f"search:{hash_key}"
    
    @staticmethod
    def search_suggestions(prefix: str, limit: int = 10) -> str:
        """Cache key for search suggestions."""
        return f"search:suggest:{prefix}:limit:{limit}"
    
    @staticmethod
    def search_popular_queries(period: str = "day", limit: int = 10) -> str:
        """Cache key for popular search queries."""
        return f"search:popular:{period}:limit:{limit}"
    
    # ============================
    # Analytics Keys
    # ============================
    
    @staticmethod
    def analytics_dashboard(date_range: str = "today") -> str:
        """Cache key for analytics dashboard."""
        return f"analytics:dashboard:{date_range}"
    
    @staticmethod
    def analytics_sales(period: str = "daily", start_date: str = None, end_date: str = None) -> str:
        """Cache key for sales analytics."""
        if start_date and end_date:
            return f"analytics:sales:{period}:{start_date}:{end_date}"
        return f"analytics:sales:{period}"
    
    @staticmethod
    def analytics_user_activity(period: str = "daily") -> str:
        """Cache key for user activity analytics."""
        return f"analytics:user_activity:{period}"
    
    @staticmethod
    def analytics_top_products(period: str = "week", limit: int = 10) -> str:
        """Cache key for top products analytics."""
        return f"analytics:top_products:{period}:limit:{limit}"
    
    @staticmethod
    def analytics_top_vendors(period: str = "week", limit: int = 10) -> str:
        """Cache key for top vendors analytics."""
        return f"analytics:top_vendors:{period}:limit:{limit}"
    
    @staticmethod
    def analytics_conversion_rate(period: str = "daily") -> str:
        """Cache key for conversion rate analytics."""
        return f"analytics:conversion_rate:{period}"
    
    # ============================
    # Session Keys
    # ============================
    
    @staticmethod
    def session(session_id: str) -> str:
        """Cache key for session data."""
        return f"session:{session_id}"
    
    @staticmethod
    def session_cart(session_id: str) -> str:
        """Cache key for anonymous session cart."""
        return f"session:{session_id}:cart"
    
    @staticmethod
    def session_locale(session_id: str) -> str:
        """Cache key for session locale."""
        return f"session:{session_id}:locale"
    
    # ============================
    # API Related Keys
    # ============================
    
    @staticmethod
    def api_response(endpoint: str, params: Dict = None) -> str:
        """Cache key for API responses."""
        import hashlib
        param_str = str(sorted(params.items())) if params else ""
        unique = f"{endpoint}:{param_str}"
        hash_key = hashlib.md5(unique.encode()).hexdigest()
        return f"api:response:{hash_key}"
    
    @staticmethod
    def api_rate_limit(client_ip: str, endpoint: str) -> str:
        """Cache key for API rate limiting."""
        return f"api:rate_limit:{client_ip}:{endpoint}"
    
    # ============================
    # Rate Limiting Keys
    # ============================
    
    @staticmethod
    def rate_limit_global(action: str) -> str:
        """Cache key for global rate limiting."""
        return f"rate_limit:global:{action}"
    
    @staticmethod
    def rate_limit_ip(ip: str, action: str) -> str:
        """Cache key for IP-based rate limiting."""
        return f"rate_limit:ip:{ip}:{action}"
    
    @staticmethod
    def rate_limit_user(user_id: int, action: str) -> str:
        """Cache key for user-based rate limiting."""
        return f"rate_limit:user:{user_id}:{action}"
    
    # ============================
    # Lock Keys (for distributed locking)
    # ============================
    
    @staticmethod
    def lock_user(user_id: int, operation: str) -> str:
        """Cache key for user operation lock."""
        return f"lock:user:{user_id}:{operation}"
    
    @staticmethod
    def lock_order(order_id: int, operation: str) -> str:
        """Cache key for order operation lock."""
        return f"lock:order:{order_id}:{operation}"
    
    @staticmethod
    def lock_product(product_id: int, operation: str = "update") -> str:
        """Cache key for product operation lock."""
        return f"lock:product:{product_id}:{operation}"
    
    @staticmethod
    def lock_inventory(product_id: int) -> str:
        """Cache key for inventory update lock."""
        return f"lock:inventory:{product_id}"
    
    @staticmethod
    def lock_payment(transaction_id: str) -> str:
        """Cache key for payment processing lock."""
        return f"lock:payment:{transaction_id}"
    
    # ============================
    # Temporary / Queue Keys
    # ============================
    
    @staticmethod
    def queue_notifications(user_id: int = None) -> str:
        """Cache key for notification queue."""
        if user_id:
            return f"queue:notifications:user:{user_id}"
        return "queue:notifications"
    
    @staticmethod
    def queue_emails() -> str:
        """Cache key for email queue."""
        return "queue:emails"
    
    @staticmethod
    def queue_sms() -> str:
        """Cache key for SMS queue."""
        return "queue:sms"
    
    @staticmethod
    def pending_payments(transaction_id: str = None) -> str:
        """Cache key for pending payments."""
        if transaction_id:
            return f"pending_payment:{transaction_id}"
        return "pending_payments"
    
    # ============================
    # Helper Methods
    # ============================
    
    @classmethod
    def pattern(cls, key_pattern: str) -> str:
        """Get cache key pattern for scanning."""
        return f"{key_pattern}*"
    
    @classmethod
    def user_pattern(cls, user_id: int = None) -> str:
        """Pattern for all user-related keys."""
        if user_id:
            return f"user:{user_id}:*"
        return "user:*"
    
    @classmethod
    def product_pattern(cls, product_id: int = None) -> str:
        """Pattern for all product-related keys."""
        if product_id:
            return f"product:{product_id}:*"
        return "product:*"
    
    @classmethod
    def vendor_pattern(cls, vendor_id: int = None) -> str:
        """Pattern for all vendor-related keys."""
        if vendor_id:
            return f"vendor:{vendor_id}:*"
        return "vendor:*"
    
    @classmethod
    def session_pattern(cls) -> str:
        """Pattern for all session keys."""
        return "session:*"
    
    @classmethod
    def lock_pattern(cls) -> str:
        """Pattern for all lock keys."""
        return "lock:*"
    
    @classmethod
    def rate_limit_pattern(cls) -> str:
        """Pattern for all rate limit keys."""
        return "rate_limit:*"


__all__ = [
    "CacheKey",
    "CacheTTL",
]