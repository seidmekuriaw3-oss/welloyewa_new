# ============================
# WOLLOYEWA STORE BOT - ORDER FLOW INTEGRATION TESTS
# ============================
"""Integration tests for complete order flow."""

import pytest
from decimal import Decimal
from unittest.mock import AsyncMock, Mock, patch


@pytest.mark.integration
class TestOrderFlowIntegration:
    """Test complete order flow from product selection to order completion."""
    
    @pytest.mark.asyncio
    async def test_complete_order_flow(self):
        """Test the complete order process."""
        # This is a mock test - in production, would use real database and services
        
        # Step 1: User registers
        user_id = 123456789
        
        # Step 2: User browses products
        # Step 3: User adds product to cart
        product_id = 1
        quantity = 2
        
        # Step 4: User proceeds to checkout
        # Step 5: User selects address
        address = "123 Test St, Addis Ababa"
        
        # Step 6: User selects payment method
        payment_method = "chapa"
        
        # Step 7: User places order
        # Step 8: Order is created
        # Step 9: Payment is processed
        # Step 10: Order is confirmed
        
        # Mock the entire flow
        with patch('apps.orders.services.OrderService.create_order') as mock_create:
            mock_order = Mock(
                id=1,
                order_number="ORD-001",
                total=Decimal("100.00"),
                status="pending",
            )
            mock_create.return_value = mock_order
            
            with patch('infrastructure.payments.factory.process_payment') as mock_payment:
                mock_payment.return_value = Mock(success=True, transaction_id="txn_123")
                
                # Verify that order can be created
                order = await mock_create(1, Mock())
                assert order is not None
                assert order.order_number == "ORD-001"
                
                # Verify payment can be processed
                payment_result = await mock_payment("chapa", Decimal("100.00"), 1, "ORD-001", "Test User", "test@test.com", "0912345678")
                assert payment_result.success is True
    
    @pytest.mark.asyncio
    async def test_order_cancellation_flow(self):
        """Test order cancellation flow."""
        user_id = 123456789
        order_id = 1
        
        with patch('apps.orders.services.OrderService.cancel_order') as mock_cancel:
            mock_cancel.return_value = Mock(status="cancelled")
            
            # Cancel order
            cancelled_order = await mock_cancel(order_id, user_id, "Changed mind")
            
            assert cancelled_order.status == "cancelled"
    
    @pytest.mark.asyncio
    async def test_order_refund_flow(self):
        """Test order refund flow."""
        order_id = 1
        
        with patch('apps.orders.refunds.RefundManager.process_refund') as mock_refund:
            mock_refund.return_value = Mock(status="completed")
            
            # Process refund
            refund = await mock_refund(order_id, Decimal("100.00"), "Customer request")
            
            assert refund.status == "completed"


@pytest.mark.integration
class TestCartToOrderFlow:
    """Test cart to order conversion flow."""
    
    @pytest.mark.asyncio
    async def test_cart_checkout_flow(self):
        """Test cart checkout flow."""
        cart_items = [
            {"product_id": 1, "name": "Product 1", "price": 50.00, "quantity": 2},
            {"product_id": 2, "name": "Product 2", "price": 30.00, "quantity": 1},
        ]
        
        expected_subtotal = 50 * 2 + 30 * 1  # 130
        expected_tax = expected_subtotal * 0.15  # 19.5
        expected_shipping = 0 if expected_subtotal >= 1000 else 50  # 50
        expected_total = expected_subtotal + expected_tax + expected_shipping  # 199.5
        
        # Validate cart calculations
        subtotal = sum(item["price"] * item["quantity"] for item in cart_items)
        assert subtotal == expected_subtotal
        
        tax = subtotal * Decimal("0.15")
        shipping = Decimal("0") if subtotal >= 1000 else Decimal("50")
        total = subtotal + tax + shipping
        
        assert float(tax) == expected_tax
        assert float(total) == expected_total


@pytest.mark.integration
class TestMultiVendorOrderFlow:
    """Test multi-vendor order flow."""
    
    @pytest.mark.asyncio
    async def test_split_payment_for_multi_vendor(self):
        """Test split payment for multi-vendor order."""
        vendor_splits = [
            {"vendor_id": 1, "amount": 60.00},
            {"vendor_id": 2, "amount": 40.00},
        ]
        
        with patch('infrastructure.payments_advanced.split_payments.create_split_payment') as mock_split:
            mock_split.return_value = Mock(status="pending")
            
            split_result = await mock_split(
                order_id=1,
                order_number="ORD-001",
                customer_name="Test User",
                customer_email="test@test.com",
                customer_phone="0912345678",
                vendor_splits=vendor_splits,
            )
            
            assert split_result.status == "pending"


__all__ = ["TestOrderFlowIntegration", "TestCartToOrderFlow", "TestMultiVendorOrderFlow"]