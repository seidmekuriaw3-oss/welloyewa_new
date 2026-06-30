# ============================
# WOLLOYEWA STORE BOT - INVENTORY SERVICE TESTS
# ============================
"""Tests for inventory management services."""

import pytest
from decimal import Decimal
from unittest.mock import AsyncMock, Mock, patch


@pytest.mark.unit
class TestInventoryService:
    """Tests for inventory service."""
    
    @pytest.mark.asyncio
    async def test_get_inventory(self):
        """Test getting inventory by product ID."""
        from apps.inventory.services import InventoryService
        
        mock_db = AsyncMock()
        mock_repo = AsyncMock()
        mock_repo.get_by_product.return_value = Mock(id=1, quantity=100, reserved_quantity=0)
        
        with patch('apps.inventory.services.InventoryRepository', return_value=mock_repo):
            service = InventoryService(mock_db)
            inventory = await service.get_inventory(product_id=1)
            
            assert inventory is not None
            assert inventory.id == 1
    
    @pytest.mark.asyncio
    async def test_add_stock(self):
        """Test adding stock to inventory."""
        from apps.inventory.services import InventoryService
        
        mock_db = AsyncMock()
        mock_inventory = Mock(id=1, quantity=50, add_stock=Mock())
        mock_repo = AsyncMock()
        mock_repo.get_by_product.return_value = mock_inventory
        
        with patch('apps.inventory.services.InventoryRepository', return_value=mock_repo):
            service = InventoryService(mock_db)
            inventory = await service.add_stock(product_id=1, quantity=10, reason="restock")
            
            mock_inventory.add_stock.assert_called_with(10, "restock")
            assert inventory is not None
    
    @pytest.mark.asyncio
    async def test_remove_stock_success(self):
        """Test removing stock successfully."""
        from apps.inventory.services import InventoryService
        
        mock_db = AsyncMock()
        mock_inventory = Mock(id=1, quantity=100, remove_stock=Mock(return_value=True))
        mock_repo = AsyncMock()
        mock_repo.get_by_product.return_value = mock_inventory
        
        with patch('apps.inventory.services.InventoryRepository', return_value=mock_repo):
            service = InventoryService(mock_db)
            inventory = await service.remove_stock(product_id=1, quantity=10, reason="sale")
            
            mock_inventory.remove_stock.assert_called_with(10, "sale")
            assert inventory is not None
    
    @pytest.mark.asyncio
    async def test_remove_stock_insufficient(self):
        """Test removing stock with insufficient quantity."""
        from apps.inventory.services import InventoryService
        from core.exceptions import InsufficientStockError
        
        mock_db = AsyncMock()
        mock_inventory = Mock(id=1, available_quantity=5, remove_stock=Mock(return_value=False))
        mock_repo = AsyncMock()
        mock_repo.get_by_product.return_value = mock_inventory
        
        with patch('apps.inventory.services.InventoryRepository', return_value=mock_repo):
            service = InventoryService(mock_db)
            
            with pytest.raises(InsufficientStockError):
                await service.remove_stock(product_id=1, quantity=10, reason="sale")
    
    @pytest.mark.asyncio
    async def test_reserve_stock(self):
        """Test reserving stock."""
        from apps.inventory.services import InventoryService
        
        mock_db = AsyncMock()
        mock_inventory = Mock(id=1, available_quantity=100, reserve=Mock(return_value=True))
        mock_repo = AsyncMock()
        mock_repo.get_by_product.return_value = mock_inventory
        mock_reservation_repo = AsyncMock()
        mock_reservation_repo.create.return_value = Mock(id=1)
        
        with patch('apps.inventory.services.InventoryRepository', return_value=mock_repo):
            with patch('apps.inventory.services.StockReservationRepository', return_value=mock_reservation_repo):
                service = InventoryService(mock_db)
                reservation = await service.reserve_stock(
                    product_id=1, quantity=10, reference_id=1, reference_type="order"
                )
                
                assert reservation is not None
    
    @pytest.mark.asyncio
    async def test_release_reservation(self):
        """Test releasing a reservation."""
        from apps.inventory.services import InventoryService
        
        mock_db = AsyncMock()
        mock_reservation = Mock(id=1, inventory_id=1, quantity=10, cancel=Mock())
        mock_inventory = Mock(id=1, reserved_quantity=10, release_reservation=Mock())
        mock_reservation_repo = AsyncMock()
        mock_reservation_repo.get_by_id.return_value = mock_reservation
        mock_inventory_repo = AsyncMock()
        mock_inventory_repo.get_by_id.return_value = mock_inventory
        
        with patch('apps.inventory.services.StockReservationRepository', return_value=mock_reservation_repo):
            with patch('apps.inventory.services.InventoryRepository', return_value=mock_inventory_repo):
                service = InventoryService(mock_db)
                await service.release_reservation(reservation_id=1)
                
                mock_reservation.cancel.assert_called_once()
                mock_inventory.release_reservation.assert_called_with(10)


@pytest.mark.unit
class TestStockMovementService:
    """Tests for stock movement service."""
    
    @pytest.mark.asyncio
    async def test_get_movements_by_date_range(self):
        """Test getting stock movements by date range."""
        from apps.inventory.services import StockMovementService
        from datetime import datetime, timedelta
        
        mock_db = AsyncMock()
        mock_repo = AsyncMock()
        mock_repo.get_by_date_range.return_value = []
        
        with patch('apps.inventory.services.InventoryMovementRepository', return_value=mock_repo):
            service = StockMovementService(mock_db)
            start_date = datetime.utcnow() - timedelta(days=30)
            end_date = datetime.utcnow()
            
            movements = await service.get_movements_by_date_range(start_date, end_date)
            
            assert movements == []
    
    @pytest.mark.asyncio
    async def test_get_movement_summary(self):
        """Test getting movement summary."""
        from apps.inventory.services import StockMovementService
        
        mock_db = AsyncMock()
        mock_repo = AsyncMock()
        mock_movements = [
            Mock(quantity=10, movement_type="restock"),
            Mock(quantity=5, movement_type="sale"),
            Mock(quantity=3, movement_type="sale"),
        ]
        mock_repo.get_by_date_range.return_value = mock_movements
        
        with patch('apps.inventory.services.InventoryMovementRepository', return_value=mock_repo):
            service = StockMovementService(mock_db)
            summary = await service.get_movement_summary()
            
            assert summary["total_in"] == 10
            assert summary["total_out"] == 8
            assert summary["net_change"] == 2


@pytest.mark.unit
class TestReservationService:
    """Tests for reservation service."""
    
    @pytest.mark.asyncio
    async def test_get_active_reservations(self):
        """Test getting active reservations."""
        from apps.inventory.services import ReservationService
        
        mock_db = AsyncMock()
        mock_repo = AsyncMock()
        mock_repo.get_active_reservations.return_value = []
        
        with patch('apps.inventory.services.StockReservationRepository', return_value=mock_repo):
            service = ReservationService(mock_db)
            reservations = await service.get_active_reservations()
            
            assert reservations == []
    
    @pytest.mark.asyncio
    async def test_cleanup_expired_reservations(self):
        """Test cleaning up expired reservations."""
        from apps.inventory.services import ReservationService
        
        mock_db = AsyncMock()
        mock_expired = [Mock(id=1), Mock(id=2)]
        mock_repo = AsyncMock()
        mock_repo.get_expired_reservations.return_value = mock_expired
        
        with patch('apps.inventory.services.StockReservationRepository', return_value=mock_repo):
            service = ReservationService(mock_db)
            count = await service.cleanup_expired_reservations()
            
            assert count == 2


@pytest.mark.unit
class TestInventoryRepository:
    """Tests for inventory repository."""
    
    @pytest.mark.asyncio
    async def test_get_by_product(self):
        """Test getting inventory by product ID."""
        from apps.inventory.repository import InventoryRepository
        
        mock_db = AsyncMock()
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none.return_value = Mock()
        mock_db.execute.return_value = mock_result
        
        repo = InventoryRepository(mock_db)
        inventory = await repo.get_by_product(product_id=1)
        
        assert inventory is not None
    
    @pytest.mark.asyncio
    async def test_get_low_stock(self):
        """Test getting low stock products."""
        from apps.inventory.repository import InventoryRepository
        
        mock_db = AsyncMock()
        mock_result = AsyncMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_db.execute.return_value = mock_result
        
        repo = InventoryRepository(mock_db)
        low_stock = await repo.get_low_stock()
        
        assert low_stock == []
    
    @pytest.mark.asyncio
    async def test_get_inventory_stats(self):
        """Test getting inventory statistics."""
        from apps.inventory.repository import InventoryRepository
        
        mock_db = AsyncMock()
        mock_result = AsyncMock()
        mock_row = Mock(
            total_products=100,
            out_of_stock=10,
            low_stock=15,
            in_stock=75,
            total_units=500,
        )
        mock_result.one.return_value = mock_row
        mock_db.execute.return_value = mock_result
        
        repo = InventoryRepository(mock_db)
        stats = await repo.get_inventory_stats()
        
        assert stats["total_products"] == 100
        assert stats["out_of_stock"] == 10
        assert stats["low_stock"] == 15
        assert stats["in_stock"] == 75
        assert stats["total_units"] == 500


@pytest.mark.unit
class TestInventoryMovementRepository:
    """Tests for inventory movement repository."""
    
    @pytest.mark.asyncio
    async def test_get_by_inventory(self):
        """Test getting movements by inventory ID."""
        from apps.inventory.repository import InventoryMovementRepository
        
        mock_db = AsyncMock()
        mock_result = AsyncMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_db.execute.return_value = mock_result
        
        repo = InventoryMovementRepository(mock_db)
        movements, total = await repo.get_by_inventory(inventory_id=1)
        
        assert movements == []
        assert total == 0


__all__ = [
    "TestInventoryService",
    "TestStockMovementService",
    "TestReservationService",
    "TestInventoryRepository",
    "TestInventoryMovementRepository",
]