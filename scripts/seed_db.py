#!/usr/bin/env python3
# ============================
# WOLLOYEWA STORE BOT - SEED DATABASE
# ============================
"""Seed the database with initial data for development."""

import asyncio
import random
from datetime import datetime, timedelta
from decimal import Decimal

from core.config import settings
from infrastructure.database.session import init_db, get_db_session
from apps.users.models import User, UserPreferences
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
        
        categories = [
            Category(name="Electronics", name_am="ኤሌክትሮኒክስ", slug="electronics", category=ProductCategory.ELECTRONICS, is_active=True),
            Category(name="Clothing", name_am="አልባሳት", slug="clothing", category=ProductCategory.CLOTHING, is_active=True),
            Category(name="Food", name_am="ምግብ", slug="food", category=ProductCategory.FOOD, is_active=True),
            Category(name="Books", name_am="መጽሐፍት", slug="books", category=ProductCategory.BOOKS, is_active=True),
            Category(name="Beauty", name_am="ውበት", slug="beauty", category=ProductCategory.BEAUTY, is_active=True),
            Category(name="Health", name_am="ጤና", slug="health", category=ProductCategory.HEALTH, is_active=True),
            Category(name="Home", name_am="ቤት", slug="home", category=ProductCategory.HOME, is_active=True),
            Category(name="Sports", name_am="ስፖርት", slug="sports", category=ProductCategory.SPORTS, is_active=True),
        ]
        
        for category in categories:
            existing = await db.execute(select(Category).where(Category.slug == category.slug))
            if not existing.scalar_one_or_none():
                db.add(category)
        
        await db.flush()
        
        # ============================
        # Seed Users
        # ============================
        print("👤 Seeding users...")
        
        # Admin user
        admin = User(
            telegram_id=5848843259,
            username="admin",
            first_name="Admin",
            role="super_admin",
            status="active",
            is_verified=True,
            language="am",
        )
        
        existing_admin = await db.execute(select(User).where(User.telegram_id == 5848843259))
        if not existing_admin.scalar_one_or_none():
            db.add(admin)
        
        # Sample customers
        customers = []
        for i in range(1, 11):
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
            customers.append(customer)
            db.add(customer)
        
        # Sample vendor
        vendor = User(
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
        db.add(vendor)
        
        await db.flush()
        
        # ============================
        # Seed Products
        # ============================
        print("📦 Seeding products...")
        
        products_data = [
            {"name": "Smartphone X100", "price": 15000, "stock": 50, "category": "Electronics"},
            {"name": "Laptop Pro", "price": 45000, "stock": 30, "category": "Electronics"},
            {"name": "Wireless Headphones", "price": 2500, "stock": 100, "category": "Electronics"},
            {"name": "Men's T-Shirt", "price": 500, "stock": 200, "category": "Clothing"},
            {"name": "Women's Dress", "price": 1200, "stock": 150, "category": "Clothing"},
            {"name": "Running Shoes", "price": 3000, "stock": 80, "category": "Sports"},
            {"name": "Coffee Beans (1kg)", "price": 400, "stock": 300, "category": "Food"},
            {"name": "Python Programming Book", "price": 800, "stock": 50, "category": "Books"},
            {"name": "Face Cream", "price": 350, "stock": 120, "category": "Beauty"},
            {"name": "Bed Sheet Set", "price": 1500, "stock": 60, "category": "Home"},
        ]
        
        vendor_user = await db.execute(select(User).where(User.username == "vendor1"))
        vendor_user = vendor_user.scalar_one_or_none()
        
        for i, p_data in enumerate(products_data, 1):
            product = Product(
                vendor_id=vendor_user.id if vendor_user else 1,
                name=p_data["name"],
                slug=p_data["name"].lower().replace(" ", "-"),
                price=Decimal(str(p_data["price"])),
                stock_quantity=p_data["stock"],
                sku=f"SKU{i:04d}",
                category=ProductCategory[p_data["category"].upper()],
                status=ProductStatus.ACTIVE.value,
                description=f"This is a high-quality {p_data['name']} product.",
                short_description=f"Great {p_data['name']} at an amazing price!",
            )
            db.add(product)
        
        await db.flush()
        
        # ============================
        # Seed Orders
        # ============================
        print("📋 Seeding orders...")
        
        products = await db.execute(select(Product))
        products = products.scalars().all()
        
        users = await db.execute(select(User).where(User.role == UserRole.CUSTOMER.value))
        users = users.scalars().all()
        
        for i, user in enumerate(users[:5]):
            # Create 2-3 orders per user
            for j in range(random.randint(2, 4)):
                order_items = random.sample(products, random.randint(1, 3))
                subtotal = sum(p.price for p in order_items)
                shipping_fee = Decimal('50') if subtotal < 1000 else Decimal('0')
                tax = subtotal * Decimal('0.15')
                total = subtotal + shipping_fee + tax
                
                order = Order(
                    order_number=f"ORD-{datetime.utcnow().strftime('%Y%m%d')}-{i:04d}{j}",
                    user_id=user.id,
                    status=random.choice([OrderStatus.DELIVERED.value, OrderStatus.SHIPPED.value, OrderStatus.PENDING.value]),
                    subtotal=subtotal,
                    shipping_fee=shipping_fee,
                    tax=tax,
                    total=total,
                    payment_method=random.choice([PaymentMethod.CHAPA.value, PaymentMethod.TELEBIRR.value]),
                    payment_status=PaymentStatus.PAID.value if j % 2 == 0 else PaymentStatus.PENDING.value,
                    shipping_address=f"Address {i}-{j}, Addis Ababa",
                    shipping_city="Addis Ababa",
                    shipping_phone=f"09{i:08d}",
                    created_at=datetime.utcnow() - timedelta(days=random.randint(1, 30)),
                )
                db.add(order)
                await db.flush()
                
                # Add order items
                for product in order_items:
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
        
        await db.commit()
        
        print("✅ Database seeding completed successfully!")


async def main():
    """Main entry point."""
    try:
        await seed_database()
    except Exception as e:
        print(f"❌ Error seeding database: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())


from sqlalchemy import select

__all__ = ["seed_database"]