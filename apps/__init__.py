# ============================
# WOLLOYEWA STORE BOT - APPLICATIONS MODULE
# ============================
"""Business application modules for the Wolloyewa Store Bot."""

from apps.common import (
    BaseModel,
    BaseRepository,
    BaseSchema,
    audit_log,
)
from apps.users import (
    UserService,
    UserRepository,
    User,
    Vendor,
)
from apps.products import (
    ProductService,
    ProductRepository,
    Product,
    Category,
    Review,
)
from apps.orders import (
    OrderService,
    OrderRepository,
    Order,
    OrderItem,
)
from apps.inventory import (
    InventoryService,
    InventoryRepository,
    Inventory,
)
from apps.marketing import (
    MarketingService,
    Coupon,
    LoyaltyProgram,
    Campaign,
)
from apps.analytics import (
    AnalyticsService,
    AnalyticsRepository,
)
from apps.support import (
    SupportService,
    Ticket,
    FAQ,
)

__all__ = [
    # Common
    "BaseModel",
    "BaseRepository",
    "BaseSchema",
    "audit_log",
    # Users
    "UserService",
    "UserRepository",
    "User",
    "Vendor",
    # Products
    "ProductService",
    "ProductRepository",
    "Product",
    "Category",
    "Review",
    # Orders
    "OrderService",
    "OrderRepository",
    "Order",
    "OrderItem",
    # Inventory
    "InventoryService",
    "InventoryRepository",
    "Inventory",
    # Marketing
    "MarketingService",
    "Coupon",
    "LoyaltyProgram",
    "Campaign",
    # Analytics
    "AnalyticsService",
    "AnalyticsRepository",
    # Support
    "SupportService",
    "Ticket",
    "FAQ",
]