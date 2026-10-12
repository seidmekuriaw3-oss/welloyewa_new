from datetime import datetime

import pytest
from sqlalchemy.dialects import postgresql

from apps.inventory.models import InventoryMovement
from apps.orders.models import Order
from apps.products.models import Product
from apps.users.models import User
from apps.users.schemas import UserResponse
from core.constants import (
    Gender,
    OrderStatus,
    PaymentMethod,
    PaymentStatus,
    ProductCategory,
    ProductStatus,
    ShippingMethod,
    UserRole,
    UserStatus,
)
from infrastructure.database import session as database_session


def test_native_enum_columns_persist_database_values():
    enum_columns = (
        (User, "role", UserRole),
        (User, "status", UserStatus),
        (User, "gender", Gender),
        (Product, "category_type", ProductCategory),
        (Product, "status", ProductStatus),
        (Order, "status", OrderStatus),
        (Order, "payment_method", PaymentMethod),
        (Order, "payment_status", PaymentStatus),
        (Order, "shipping_method", ShippingMethod),
    )

    for model, column_name, enum_type in enum_columns:
        assert model.__table__.c[column_name].type.enums == [
            member.value for member in enum_type
        ]

    bind_processor = User.__table__.c.role.type.bind_processor(postgresql.dialect())
    assert bind_processor is not None
    assert bind_processor("CUSTOMER") == "customer"


def test_user_model_normalizes_uppercase_enum_names():
    user = User(
        telegram_id=123456,
        first_name="Test",
        role="CUSTOMER",
        status="ACTIVE",
        gender="FEMALE",
    )

    assert user.role is UserRole.CUSTOMER
    assert user.status is UserStatus.ACTIVE
    assert user.gender is Gender.FEMALE


def test_user_schema_enum_names_are_case_insensitive():
    assert UserRole("CUSTOMER") is UserRole.CUSTOMER
    assert UserStatus("ACTIVE") is UserStatus.ACTIVE
    assert ProductCategory("ELECTRONICS") is ProductCategory.ELECTRONICS
    response = UserResponse(
        id=1,
        telegram_id=123456,
        first_name="Test",
        role="CUSTOMER",
        status="ACTIVE",
        gender="FEMALE",
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    assert response.role is UserRole.CUSTOMER


def test_product_category_alias_maps_to_category_type():
    product = Product(
        vendor_id=1,
        name="Test product",
        slug="test-product",
        price=10,
        sku="TEST-001",
        category="ELECTRONICS",
    )

    assert product.category_type is ProductCategory.ELECTRONICS
    assert product.category is ProductCategory.ELECTRONICS
    assert Product.category == Product.category_type


def test_migration_columns_are_mapped_by_models():
    assert "preferred_language" in User.__table__.c
    assert "notification_settings" in User.__table__.c
    assert "reserved_quantity" in Product.__table__.c
    assert "updated_at" in InventoryMovement.__table__.c
    assert {
        "payment_attempts",
        "last_payment_error",
        "reconciliation_status",
    } <= set(Order.__table__.c.keys())

    assert User.__table__.c.verified_at.type.python_type is datetime


def test_session_factory_proxy_requires_database_initialization(monkeypatch):
    monkeypatch.setattr(database_session._session_manager, "_sessionmaker", None)

    with pytest.raises(RuntimeError, match="call init_db"):
        database_session.AsyncSessionLocal()
