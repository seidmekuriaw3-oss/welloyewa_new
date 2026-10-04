"""Tests for centralized cache key and TTL helpers."""

import pytest

from core.cache_keys import CacheKey, CacheTTL


@pytest.mark.unit
def test_cache_ttls_are_stable_for_domain_objects():
    assert CacheTTL.for_user(1) == CacheTTL.MEDIUM
    assert CacheTTL.for_product(1) == CacheTTL.LONG
    assert CacheTTL.for_product_list("phones") == CacheTTL.MEDIUM
    assert CacheTTL.for_order(1) == CacheTTL.STANDARD
    assert CacheTTL.for_session("session") == CacheTTL.SESSION
    assert CacheTTL.for_analytics("sales") == CacheTTL.VERY_LONG
    assert CacheTTL.PERMANENT is None


@pytest.mark.unit
def test_user_vendor_and_product_keys_include_scope_and_filters():
    assert CacheKey.user(7) == "user:7"
    assert CacheKey.user_by_telegram(99) == "user:telegram:99"
    assert CacheKey.user_by_email("User@Example.COM") == "user:email:user@example.com"
    assert CacheKey.user_by_phone("0912345678") == "user:phone:0912345678"
    assert CacheKey.user_preferences(7) == "user:7:preferences"
    assert CacheKey.user_cart(7) == "user:7:cart"
    assert CacheKey.user_wishlist(7) == "user:7:wishlist"
    assert CacheKey.user_orders(7) == "user:7:orders"
    assert CacheKey.user_orders(7, "paid") == "user:7:orders:paid"
    assert CacheKey.user_notifications(7, unread_only=True) == "user:7:notifications:unread"
    assert CacheKey.user_session("abc") == "session:abc"
    assert CacheKey.user_otp("abc", "login") == "otp:login:abc"
    assert CacheKey.user_rate_limit(7, "search") == "rate_limit:user:7:search"

    assert CacheKey.vendor(3) == "vendor:3"
    assert CacheKey.vendor_by_user(7) == "vendor:user:7"
    assert CacheKey.vendor_products(3, "active") == "vendor:3:products:active"
    assert CacheKey.vendor_orders(3) == "vendor:3:orders"
    assert CacheKey.vendor_stats(3) == "vendor:3:stats"
    assert CacheKey.vendor_earnings(3, "weekly") == "vendor:3:earnings:weekly"

    assert CacheKey.product(4) == "product:4"
    assert CacheKey.product_by_sku("SKU-4") == "product:sku:SKU-4"
    assert CacheKey.product_by_slug("phone") == "product:slug:phone"
    assert CacheKey.product_list("phones", 3, "price", 2, 10) == (
        "products:cat:phones:vendor:3:sort:price:p:2:ps:10"
    )
    assert CacheKey.product_reviews(4, 2) == "product:4:reviews:p:2"
    assert CacheKey.product_rating(4) == "product:4:rating"
    assert CacheKey.product_stock(4) == "product:4:stock"
    assert CacheKey.product_categories() == "products:categories"
    assert CacheKey.featured_products(5) == "products:featured:limit:5"
    assert CacheKey.popular_products(5, "month") == "products:popular:month:limit:5"
    assert CacheKey.new_products(5) == "products:new:limit:5"
    assert CacheKey.discounted_products(5) == "products:discounted:limit:5"


@pytest.mark.unit
def test_order_search_analytics_and_session_keys_are_deterministic():
    assert CacheKey.order(8) == "order:8"
    assert CacheKey.order_by_number("ORD-8") == "order:number:ORD-8"
    assert CacheKey.order_items(8) == "order:8:items"
    assert CacheKey.order_tracking(8) == "order:8:tracking"
    assert CacheKey.order_invoice(8) == "order:8:invoice"
    assert CacheKey.search_query("phone", {"category": 2}, 1) == CacheKey.search_query(
        "phone", {"category": 2}, 1
    )
    assert CacheKey.search_suggestions("ph", 5) == "search:suggest:ph:limit:5"
    assert CacheKey.search_popular_queries("month", 5) == "search:popular:month:limit:5"
    assert CacheKey.analytics_dashboard("week") == "analytics:dashboard:week"
    assert CacheKey.analytics_sales("monthly") == "analytics:sales:monthly"
    assert CacheKey.analytics_sales("monthly", "2024-01-01", "2024-01-31") == (
        "analytics:sales:monthly:2024-01-01:2024-01-31"
    )
    assert CacheKey.analytics_user_activity("week") == "analytics:user_activity:week"
    assert CacheKey.analytics_top_products("month", 5) == "analytics:top_products:month:limit:5"
    assert CacheKey.analytics_top_vendors("month", 5) == "analytics:top_vendors:month:limit:5"
    assert CacheKey.analytics_conversion_rate("month") == "analytics:conversion_rate:month"
    assert CacheKey.session("abc") == "session:abc"
    assert CacheKey.session_cart("abc") == "session:abc:cart"
    assert CacheKey.session_locale("abc") == "session:abc:locale"


@pytest.mark.unit
def test_api_rate_limit_lock_queue_and_pattern_keys():
    assert CacheKey.api_response("/products", {"page": 1}) == CacheKey.api_response(
        "/products", {"page": 1}
    )
    assert CacheKey.api_rate_limit("127.0.0.1", "/products") == "api:rate_limit:127.0.0.1:/products"
    assert CacheKey.rate_limit_global("login") == "rate_limit:global:login"
    assert CacheKey.rate_limit_ip("127.0.0.1", "login") == "rate_limit:ip:127.0.0.1:login"
    assert CacheKey.rate_limit_user(7, "login") == "rate_limit:user:7:login"
    assert CacheKey.lock_user(7, "update") == "lock:user:7:update"
    assert CacheKey.lock_order(8, "cancel") == "lock:order:8:cancel"
    assert CacheKey.lock_product(4) == "lock:product:4:update"
    assert CacheKey.lock_inventory(4) == "lock:inventory:4"
    assert CacheKey.lock_payment("txn") == "lock:payment:txn"
    assert CacheKey.queue_notifications() == "queue:notifications"
    assert CacheKey.queue_notifications(7) == "queue:notifications:user:7"
    assert CacheKey.queue_emails() == "queue:emails"
    assert CacheKey.queue_sms() == "queue:sms"
    assert CacheKey.pending_payments() == "pending_payments"
    assert CacheKey.pending_payments("txn") == "pending_payment:txn"
    assert CacheKey.pattern("user:") == "user:*"
    assert CacheKey.user_pattern() == "user:*"
    assert CacheKey.user_pattern(7) == "user:7:*"
    assert CacheKey.product_pattern(4) == "product:4:*"
    assert CacheKey.vendor_pattern() == "vendor:*"
    assert CacheKey.session_pattern() == "session:*"
    assert CacheKey.lock_pattern() == "lock:*"
    assert CacheKey.rate_limit_pattern() == "rate_limit:*"
