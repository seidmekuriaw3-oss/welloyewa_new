# ============================
# WOLLOYEWA STORE BOT - USER REPOSITORIES
# ============================
"""Database repositories for User and Vendor models."""

from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.common.repository import BaseRepository
from apps.users.models import User, Vendor


class UserRepository(BaseRepository[User]):
    """Repository for User model operations."""

    def __init__(self, db: AsyncSession):
        super().__init__(User, db)

    async def get_by_telegram(self, telegram_id: int) -> User | None:
        """Get user by Telegram ID."""
        query = select(User).where(User.telegram_id == telegram_id)
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def get_by_phone(self, phone_number: str) -> User | None:
        """Get user by phone number."""
        query = select(User).where(User.phone_number == phone_number)
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def get_by_email(self, email: str) -> User | None:
        """Get user by email address."""
        query = select(User).where(User.email == email)
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def get_by_username(self, username: str) -> User | None:
        """Get user by username."""
        query = select(User).where(User.username == username)
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def get_active_users(
        self,
        limit: int = 100,
        offset: int = 0,
        role: str | None = None,
    ) -> list[User]:
        """Get active users with optional role filter."""
        query = select(User).where(User.status == "active", User.is_deleted.is_(False))

        if role:
            query = query.where(User.role == role)

        query = query.order_by(User.created_at.desc()).offset(offset).limit(limit)
        result = await self.db.execute(query)
        return result.scalars().all()

    async def get_users_by_role(self, role: str, limit: int = 100) -> list[User]:
        """Get users by role."""
        query = select(User).where(User.role == role, User.is_deleted.is_(False))
        query = query.order_by(User.created_at.desc()).limit(limit)
        result = await self.db.execute(query)
        return result.scalars().all()

    async def update_last_active(self, user_id: int, ip_address: str | None = None) -> None:
        """Update user's last active timestamp."""
        data = {"last_active": datetime.utcnow()}
        if ip_address:
            data["last_login_ip"] = ip_address

        await self.update(user_id, data)

    async def get_user_count_by_role(self) -> dict[str, int]:
        """Get count of users by role."""
        query = select(User.role, func.count()).where(User.is_deleted.is_(False)).group_by(User.role)
        result = await self.db.execute(query)
        return dict(result.all())

    async def get_recent_users(self, days: int = 7, limit: int = 50) -> list[User]:
        """Get users who joined in the last N days."""
        cutoff = datetime.utcnow() - timedelta(days=days)
        query = select(User).where(User.created_at >= cutoff, User.is_deleted.is_(False))
        query = query.order_by(User.created_at.desc()).limit(limit)
        result = await self.db.execute(query)
        return result.scalars().all()

    async def search_users(
        self,
        query: str,
        limit: int = 20,
    ) -> list[User]:
        """Search users by name, username, or phone."""
        search_pattern = f"%{query}%"
        stmt = (
            select(User)
            .where(
                (User.first_name.ilike(search_pattern))
                | (User.last_name.ilike(search_pattern))
                | (User.username.ilike(search_pattern))
                | (User.phone_number.ilike(search_pattern))
                | (User.email.ilike(search_pattern))
            )
            .where(User.is_deleted.is_(False))
            .limit(limit)
        )

        result = await self.db.execute(stmt)
        return result.scalars().all()


class VendorRepository(BaseRepository[Vendor]):
    """Repository for Vendor model operations."""

    def __init__(self, db: AsyncSession):
        super().__init__(Vendor, db)

    async def get_by_user_id(self, user_id: int) -> Vendor | None:
        """Get vendor by user ID."""
        query = select(Vendor).where(Vendor.user_id == user_id)
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def get_by_business_name(self, business_name: str) -> Vendor | None:
        """Get vendor by business name."""
        query = select(Vendor).where(Vendor.business_name == business_name)
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def get_by_license(self, license_number: str) -> Vendor | None:
        """Get vendor by business license number."""
        query = select(Vendor).where(Vendor.business_license == license_number)
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def get_approved_vendors(
        self,
        limit: int = 100,
        offset: int = 0,
    ) -> list[Vendor]:
        """Get approved vendors."""
        query = select(Vendor).where(Vendor.is_approved)
        query = query.order_by(Vendor.rating.desc()).offset(offset).limit(limit)
        result = await self.db.execute(query)
        return result.scalars().all()

    async def get_pending_vendors(self, limit: int = 100) -> list[Vendor]:
        """Get vendors awaiting approval."""
        query = select(Vendor).where(Vendor.is_approved.is_(False), Vendor.rejected_at.is_(None))
        query = query.order_by(Vendor.created_at.asc()).limit(limit)
        result = await self.db.execute(query)
        return result.scalars().all()

    async def get_top_vendors(self, limit: int = 10) -> list[Vendor]:
        """Get top-rated vendors."""
        query = select(Vendor).where(Vendor.is_approved)
        query = query.order_by(Vendor.rating.desc(), Vendor.total_sales.desc()).limit(limit)
        result = await self.db.execute(query)
        return result.scalars().all()

    async def update_rating(self, vendor_id: int, new_rating: float) -> None:
        """Update vendor's average rating."""
        await self.update(vendor_id, {"rating": new_rating})

    async def increment_sales(self, vendor_id: int, amount: int = 1) -> None:
        """Increment vendor's total sales count."""
        vendor = await self.get_by_id(vendor_id)
        if vendor:
            await self.update(vendor_id, {"total_sales": vendor.total_sales + amount})

    async def get_vendor_stats(self) -> dict[str, Any]:
        """Get overall vendor statistics."""
        query = select(
            func.count().label("total"),
            func.sum(case((Vendor.is_approved, 1), else_=0)).label("approved"),
            func.sum(case((Vendor.is_approved.is_(False), 1), else_=0)).label("pending"),
        ).select_from(Vendor)

        result = await self.db.execute(query)
        row = result.one()

        return {
            "total_vendors": row.total or 0,
            "approved_vendors": row.approved or 0,
            "pending_vendors": row.pending or 0,
        }


__all__ = ["UserRepository", "VendorRepository"]
