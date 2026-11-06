from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.dialects import postgresql

from apps.inventory.schemas import InventoryCreate, InventoryUpdate
from apps.inventory.services import InventoryService
from apps.orders.schemas import OrderStatusUpdate
from apps.orders.services import OrderService
from apps.products.repository import ProductRepository
from apps.products.schemas import ProductCreate, ProductUpdate
from apps.products.services import ProductService
from core.constants import OrderStatus, ProductStatus
from core.events import PRODUCT_APPROVED, PRODUCT_REJECTED
from core.exceptions import ValidationError


@pytest.mark.asyncio
async def test_sync_inventory_uses_inventory_create_schema_when_missing():
    service = ProductService(MagicMock())
    service.inventory_service.get_inventory = AsyncMock(return_value=None)
    service.inventory_service.create_inventory = AsyncMock()
    product = SimpleNamespace(
        id=17,
        vendor_id=8,
        sku="SKU-17",
        barcode="BAR-17",
    )

    await service._sync_inventory(product, quantity=6, low_stock_threshold=3)

    service.inventory_service.create_inventory.assert_awaited_once()
    inventory_data = service.inventory_service.create_inventory.await_args.args[0]
    assert isinstance(inventory_data, InventoryCreate)
    assert inventory_data.product_id == 17
    assert inventory_data.vendor_id == 8
    assert inventory_data.quantity == 6
    assert inventory_data.low_stock_threshold == 3
    assert inventory_data.sku == "SKU-17"


@pytest.mark.asyncio
async def test_sync_inventory_uses_update_schema_when_inventory_exists():
    service = ProductService(MagicMock())
    service.inventory_service.get_inventory = AsyncMock(return_value=object())
    service.inventory_service.update_inventory = AsyncMock()
    product = SimpleNamespace(
        id=17,
        vendor_id=8,
        sku="SKU-17",
        barcode="BAR-17",
    )

    await service._sync_inventory(product, quantity=6, low_stock_threshold=3)

    service.inventory_service.update_inventory.assert_awaited_once()
    product_id, inventory_data = service.inventory_service.update_inventory.await_args.args
    assert product_id == 17
    assert isinstance(inventory_data, InventoryUpdate)
    assert inventory_data.quantity == 6
    assert inventory_data.low_stock_threshold == 3


@pytest.mark.asyncio
async def test_inventory_update_persists_explicit_null_and_uses_reason_only_for_log():
    service = InventoryService(MagicMock())
    service.inventory_repo.get_by_product = AsyncMock(
        return_value=SimpleNamespace(id=4, quantity=2)
    )
    updated_inventory = SimpleNamespace(id=4, quantity=5)
    service.inventory_repo.update = AsyncMock(return_value=updated_inventory)
    service._record_movement = AsyncMock()
    service._check_stock_alerts = AsyncMock()

    await service.update_inventory(
        17,
        InventoryUpdate(quantity=5, barcode=None, reason="manual correction"),
    )

    _, update_data = service.inventory_repo.update.await_args.args
    assert update_data == {"quantity": 5, "barcode": None}
    assert service.inventory_repo.update.await_args.kwargs["partial"] is False
    service._record_movement.assert_awaited_once()
    assert service._record_movement.await_args.kwargs["reason"] == "manual correction"
    service._check_stock_alerts.assert_awaited_once_with(updated_inventory)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("quantity", "operation"),
    [(-1, "set"), (0, "add"), (0, "subtract"), (1, "multiply")],
)
async def test_update_stock_rejects_invalid_adjustments(quantity, operation):
    service = ProductService(MagicMock())
    service.get_product = AsyncMock()

    with pytest.raises(ValidationError):
        await service.update_stock(1, quantity, operation)

    service.get_product.assert_not_awaited()


@pytest.mark.asyncio
async def test_vendor_cannot_create_active_product():
    service = ProductService(MagicMock())
    data = ProductCreate(
        name="Unauthorized active product",
        price=10,
        sku="ACTIVE-001",
        status=ProductStatus.ACTIVE,
    )

    with pytest.raises(ValidationError, match="Only administrators"):
        await service.create_product(8, data)


@pytest.mark.asyncio
async def test_vendor_created_products_are_always_pending_until_review():
    service = ProductService(MagicMock())
    product = SimpleNamespace(
        id=31,
        vendor_id=8,
        category_id=None,
        name="Pending product",
        price=12,
        status=ProductStatus.PENDING,
    )
    service.product_repo.get_by_slug = AsyncMock(return_value=None)
    service.product_repo.create = AsyncMock(return_value=product)
    service._sync_inventory = AsyncMock()
    service.category_repo.get_by_id = AsyncMock()

    with patch("apps.products.services.emit_event", new_callable=AsyncMock):
        created = await service.create_product(
            8,
            ProductCreate(
                name="Pending product",
                price=12,
                sku="PENDING-31",
                status=ProductStatus.DRAFT,
            ),
        )

    saved_data = service.product_repo.create.await_args.args[0]
    assert created is product
    assert saved_data["status"] == ProductStatus.PENDING


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("approved", "expected_status", "event_name"),
    [
        (True, ProductStatus.ACTIVE, PRODUCT_APPROVED),
        (False, ProductStatus.REJECTED, PRODUCT_REJECTED),
    ],
)
async def test_admin_review_transitions_pending_product_and_emits_lifecycle_event(
    approved,
    expected_status,
    event_name,
):
    service = ProductService(MagicMock())
    pending = SimpleNamespace(id=31, status=ProductStatus.PENDING, category_id=None)
    updated = SimpleNamespace(
        id=31,
        vendor_id=8,
        status=expected_status,
        category_id=None,
    )
    service.get_product = AsyncMock(return_value=pending)
    service.product_repo.update = AsyncMock(return_value=updated)

    with patch("apps.products.services.emit_event", new_callable=AsyncMock) as emit:
        result = await service.review_product(
            31,
            approved=approved,
            reason="Please add product dimensions." if not approved else None,
        )

    assert result is updated
    assert service.product_repo.update.await_args.args[1] == {"status": expected_status}
    assert emit.await_args.args[0] == event_name
    if not approved:
        assert emit.await_args.args[1]["reason"] == "Please add product dimensions."


@pytest.mark.asyncio
async def test_vendor_cannot_approve_product_during_update():
    service = ProductService(MagicMock())
    service.get_product = AsyncMock(
        return_value=SimpleNamespace(id=17, vendor_id=8, name="Product")
    )
    service.product_repo.update = AsyncMock()

    with pytest.raises(ValidationError, match="Only administrators"):
        await service.update_product(
            17,
            8,
            ProductUpdate(status=ProductStatus.ACTIVE),
        )

    service.product_repo.update.assert_not_awaited()


@pytest.mark.asyncio
async def test_stock_subtraction_is_atomic_and_cannot_go_negative():
    result = MagicMock()
    result.scalar_one_or_none.return_value = None
    db = MagicMock()
    db.execute = AsyncMock(return_value=result)
    db.flush = AsyncMock()
    repository = ProductRepository(db)

    await repository.adjust_stock(17, 4, "subtract")

    statement = db.execute.await_args.args[0]
    sql = str(statement.compile(dialect=postgresql.dialect()))
    assert "products.stock_quantity >= " in sql
    assert "products.is_deleted IS false" in sql
    db.flush.assert_awaited_once()


@pytest.mark.asyncio
async def test_public_product_query_excludes_inactive_and_deleted_products():
    result = MagicMock()
    result.scalars.return_value.all.return_value = []
    db = MagicMock()
    db.scalar = AsyncMock(return_value=0)
    db.execute = AsyncMock(return_value=result)
    repository = ProductRepository(db)

    products, total = await repository.get_public_products(category="clothing")

    assert products == []
    assert total == 0
    sql = str(db.execute.await_args.args[0].compile(dialect=postgresql.dialect()))
    assert "products.status = " in sql
    assert "products.is_deleted IS false" in sql
    assert "products.category_type = " in sql


@pytest.mark.asyncio
async def test_vendor_product_pagination_returns_matching_total():
    product = object()
    result = MagicMock()
    result.scalars.return_value.all.return_value = [product]
    db = MagicMock()
    db.scalar = AsyncMock(return_value=12)
    db.execute = AsyncMock(return_value=result)
    repository = ProductRepository(db)

    products, total = await repository.get_by_vendor_with_count(
        vendor_id=8,
        limit=1,
        offset=4,
    )

    assert products == [product]
    assert total == 12


@pytest.mark.asyncio
async def test_vendor_cancellation_releases_reserved_product_stock():
    service = OrderService(MagicMock())
    order = SimpleNamespace(id=23, user_id=7, status=OrderStatus.PROCESSING)
    item = SimpleNamespace(
        vendor_id=8,
        vendor_status=OrderStatus.PROCESSING,
        product_id=17,
        quantity=2,
    )
    service.get_order = AsyncMock(return_value=order)
    service.order_item_repo.get_by_order = AsyncMock(return_value=[item])
    service.product_service.release_stock = AsyncMock()
    service.db.flush = AsyncMock()

    await service.update_vendor_order_status(
        23,
        8,
        OrderStatusUpdate(status=OrderStatus.CANCELLED),
        11,
    )

    service.product_service.release_stock.assert_awaited_once_with(17, 2)
    assert item.vendor_status == OrderStatus.CANCELLED
