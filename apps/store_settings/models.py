"""Database-backed operational settings that are safe to change at runtime."""

from datetime import datetime

from sqlalchemy import JSON, Boolean, DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from infrastructure.database.base import Base


class StoreSettings(Base):
    """Singleton configuration for store operations, never for environment secrets."""

    __tablename__ = "store_settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, default=1)
    store_open: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    currency_code: Mapped[str] = mapped_column(String(3), nullable=False, default="ETB")
    enabled_payment_methods: Mapped[list[str]] = mapped_column(
        JSON, nullable=False, default=lambda: ["chapa", "telebirr", "cbe", "cod"]
    )
    notification_settings: Mapped[dict[str, bool]] = mapped_column(
        JSON,
        nullable=False,
        default=lambda: {
            "customer_orders": True,
            "vendor_updates": True,
            "admin_alerts": True,
            "support_updates": True,
        },
    )
    maintenance_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )
