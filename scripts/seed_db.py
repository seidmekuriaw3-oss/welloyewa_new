#!/usr/bin/env python3
# ============================
# WOLLOYEWA STORE BOT - SEED DATABASE
# ============================
"""Seed the database with initial data for development."""

import asyncio
import random
from datetime import datetime, timedelta
from decimal import Decimal

from sqlalchemy import select

from core.config import settings
from infrastructure.database.session import init_db, get_db_session
from apps.users.models import User, Vendor
from apps.products.models import Product, Category
from apps.orders.models import Order, OrderItem
from core.constants import UserRole, ProductStatus, ProductCategory, OrderStatus, PaymentStatus, PaymentMethod


async def seed_database() -> None:
    """Seed the database with initial data."""
    print("🌱 Seeding database...")

    await init_db()

    async for db in get_db_session():
        # ============================
        # Seed Categories
        # ============================
        print("📁 Seeding categories...")

        categories_data = [
            {"name": "Electronics",  "name_am": "ኤሌክትሮኒክስ", "slug": "electronics"},
            {"name": "Clothing",     "name_am": "አልባሳት",       "slug": "clothing"},
            {"name": "Food",         "name_am": "ምግብ",          "slug": "food"},
            {"name": "Books",        "name_am": "መጽሐፍት",       "slug": "books"},
            {"name": "Beauty",       "name_am": "ውበት",          "slug": "beauty"},
            {"name": "Health",       "name_am": "ጤና",           "slug": "health"},
            {"name": "Home",         "name_am": "ቤት",           "slug": "home"},
            {"name": "Sports",       "name_am": "ስፖርት",         "slug": "sports"},
        ]

        category_map = {}
        for c_data in categories_data:
            result = await db.execute(select(Category).where(Category.slug == c_data["slug"]))
            existing = result.scalar_one_or_none()
            if not existing:
                cat = Category(
                    name=c_data["name"],
                    name_am=c_data["name_am"],
                    slug=c_data["slug"],
                    is_active=True,
                )
                db.add(cat)
                await db.flush()
                category_map[c_data["slug"]] = cat.id
            else:
                category_map[c_data["slug"]] = existing.id

        await db.flush()

        # ============================
        # Seed Users
        # ============================
        print("👤 Seeding users...")

        # Admin user
        result = await db.execute(select(User).where(User.telegram_id == 5848843259))
        if not result.scalar_one_or_none():
            admin = User(
                telegram_id=5848843259,
                username="admin",
                first_name="Admin",
                role="super_admin",
                status="active",
                is_verified=True,
                language="am",
            )
            db.add(admin)

        # Sample customers
        customers = []
        for i in range(1, 11):
            result = await db.execute(select(User).where(User.telegram_id == 700000000 + i))
            existing = result.scalar_one_or_none()
            if not existing:
                customer = User(
                    telegram_id=700000000 + i,
                    username=f"customer{i}",
                    first_name=f"Customer{i}",
                    last_name=f"Last{i}",
                    phone_number=f"09{i:08d}",
                    email=f"customer{i}@example.com",
                    role=UserRole.CUSTOMER.value,
                    status="active",
                    is_verified=True,
                )
                db.add(customer)
                customers.append(customer)
            else:
                customers.append(existing)

        # Sample vendor
        result = await db.execute(select(User).where(User.telegram_id == 700000100))
        vendor_user = result.scalar_one_or_none()
        if not vendor_user:
            vendor_user = User(
                telegram_id=700000100,
                username="vendor1",
                first_name="Vendor",
                last_name="One",
                phone_number="0912345678",
                email="vendor@example.com",
                role=UserRole.VENDOR.value,
                status="active",
                is_verified=True,
            )
            db.add(vendor_user)

        await db.flush()

        # Create Vendor profile for the vendor user
        result = await db.execute(select(Vendor).where(Vendor.user_id == vendor_user.id))
        vendor_profile = result.scalar_one_or_none()
        if not vendor_profile:
            vendor_profile = Vendor(
                user_id=vendor_user.id,
                business_name="Wolloyewa Sample Store",
                business_address="Bole Road, Addis Ababa",
                business_phone="0912345678",
                business_email="vendor@example.com",
                description="Official sample vendor for Wolloyewa marketplace.",
                is_approved=True,
                rating=4.5,
                total_sales=0,
                total_products=0,
            )
            db.add(vendor_profile)
            await db.flush()

        # ============================
        # Seed Products
        # ============================
        print("📦 Seeding products...")

        products_data = [
            {"name": "Smartphone X100",      "price": 15000, "stock": 50,  "slug": "electronics",  "cat": ProductCategory.ELECTRONICS},
            {"name": "Laptop Pro",           "price": 45000, "stock": 30,  "slug": "electronics",  "cat": ProductCategory.ELECTRONICS},
            {"name": "Wireless Headphones",  "price": 2500,  "stock": 100, "slug": "electronics",  "cat": ProductCategory.ELECTRONICS},
            {"name": "Men's T-Shirt",        "price": 500,   "stock": 200, "slug": "clothing",     "cat": ProductCategory.CLOTHING},
            {"name": "Women's Dress",        "price": 1200,  "stock": 150, "slug": "clothing",     "cat": ProductCategory.CLOTHING},
            {"name": "Running Shoes",        "price": 3000,  "stock": 80,  "slug": "sports",       "cat": ProductCategory.SPORTS},
            {"name": "Coffee Beans (1kg)",   "price": 400,   "stock": 300, "slug": "food",         "cat": ProductCategory.FOOD},
            {"name": "Python Programming Book", "price": 800, "stock": 50, "slug": "books",        "cat": ProductCategory.BOOKS},
            {"name": "Face Cream",           "price": 350,   "stock": 120, "slug": "beauty",       "cat": ProductCategory.BEAUTY},
            {"name": "Bed Sheet Set",        "price": 1500,  "stock": 60,  "slug": "home",         "cat": ProductCategory.HOME},
        ]

        seeded_products = []
        for i, p_data in enumerate(products_data, 1):
            sku = f"SKU{i:04d}"
            result = await db.execute(select(Product).where(Product.sku == sku))
            existing = result.scalar_one_or_none()
            if not existing:
                product = Product(
                    vendor_id=vendor_profile.id,
                    name=p_data["name"],
                    slug=p_data["name"].lower().replace(" ", "-").replace("'", ""),
                    price=Decimal(str(p_data["price"])),
                    stock_quantity=p_data["stock"],
                    sku=sku,
                    category_id=category_map.get(p_data["slug"]),
                    category_type=p_data["cat"],
                    status=ProductStatus.ACTIVE.value,
                    description=f"This is a high-quality {p_data['name']} product.",
                    short_description=f"Great {p_data['name']} at an amazing price!",
                    is_featured=(i <= 3),
                )
                db.add(product)
                await db.flush()
                seeded_products.append(product)
            else:
                seeded_products.append(existing)

        await db.flush()

        # ============================
        # Seed Orders
        # ============================
        print("📋 Seeding orders...")

        # Reload fresh customers from DB
        result = await db.execute(select(User).where(User.role == UserRole.CUSTOMER.value))
        all_customers = result.scalars().all()

        result = await db.execute(select(Product))
        all_products = result.scalars().all()

        order_count = 0
        for i, user in enumerate(all_customers[:5]):
            for j in range(random.randint(2, 3)):
                order_items_products = random.sample(all_products, random.randint(1, 3))
                subtotal = sum(p.price for p in order_items_products)
                shipping_fee = Decimal("50") if subtotal < 1000 else Decimal("0")
                tax = subtotal * Decimal("0.15")
                total = subtotal + shipping_fee + tax

                order_num = f"ORD-{datetime.utcnow().strftime('%Y%m%d')}-{i:03d}{j}"
                # Skip if already exists
                result = await db.execute(select(Order).where(Order.order_number == order_num))
                if result.scalar_one_or_none():
                    continue

                order = Order(
                    order_number=order_num,
                    user_id=user.id,
                    vendor_id=vendor_profile.id,
                    status=random.choice([
                        OrderStatus.DELIVERED.value,
                        OrderStatus.SHIPPED.value,
                        OrderStatus.PENDING.value,
                    ]),
                    subtotal=subtotal,
                    shipping_fee=shipping_fee,
                    tax=tax,
                    total=total,
                    payment_method=random.choice([
                        PaymentMethod.CHAPA.value,
                        PaymentMethod.TELEBIRR.value,
                    ]),
                    payment_status=PaymentStatus.PAID.value if j % 2 == 0 else PaymentStatus.PENDING.value,
                    shipping_address=f"Address {i}-{j}, Addis Ababa",
                    shipping_city="Addis Ababa",
                    shipping_phone=f"09{i:08d}",
                    created_at=datetime.utcnow() - timedelta(days=random.randint(1, 30)),
                )
                db.add(order)
                await db.flush()

                for product in order_items_products:
                    order_item = OrderItem(
                        order_id=order.id,
                        product_id=product.id,
                        product_name=product.name,
                        product_sku=product.sku,
                        quantity=random.randint(1, 3),
                        unit_price=product.price,
                        total_price=product.price,
                    )
                    db.add(order_item)

                order_count += 1

        await db.commit()
        print(f"✅ Database seeding completed! Categories: {len(categories_data)}, Products: {len(seeded_products)}, Orders: {order_count}")


async def main():
    """Main entry point."""
    try:
        await seed_database()
    except Exception as e:
        import traceback
        print(f"❌ Error seeding database: {e}")
        traceback.print_exc()
        raise


if __name__ == "__main__":
    asyncio.run(main())


__all__ = ["seed_database"]
