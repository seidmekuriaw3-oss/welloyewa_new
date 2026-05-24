# ============================
# WOLLOYEWA STORE BOT - PAYMENT SERVICE TESTS
# ============================
"""Tests for payment processing services."""

import pytest
from decimal import Decimal
from unittest.mock import AsyncMock, Mock, patch


@pytest.mark.unit
class TestPaymentProvider:
    """Tests for payment provider base class."""
    
    @pytest.mark.asyncio
    async def test_chapa_provider_initialization(self):
        """Test Chapa provider initialization."""
        from infrastructure.payments.chapa import ChapaProvider
        
        with patch('infrastructure.payments.chapa.settings') as mock_settings:
            mock_settings.CHAPA_API_URL = "https://api.chapa.co/v1"
            mock_settings.CHAPA_SECRET_KEY = "test_key"
            
            provider = ChapaProvider()
            assert provider.name == "chapa"
            assert provider.api_url == "https://api.chapa.co/v1"
    
    @pytest.mark.asyncio
    async def test_telebirr_provider_initialization(self):
        """Test Telebirr provider initialization."""
        from infrastructure.payments.telebirr import TelebirrProvider
        
        with patch('infrastructure.payments.telebirr.settings') as mock_settings:
            mock_settings.TELEBIRR_API_URL = "https://api.ethiotelecom.et/telebirr"
            mock_settings.TELEBIRR_APP_ID = "test_app_id"
            
            provider = TelebirrProvider()
            assert provider.name == "telebirr"
    
    @pytest.mark.asyncio
    async def test_cbe_birr_provider_initialization(self):
        """Test CBE Birr provider initialization."""
        from infrastructure.payments.cbe_birr import CBEBirrProvider
        
        with patch('infrastructure.payments.cbe_birr.settings') as mock_settings:
            mock_settings.CBE_BIRR_API_URL = "https://cbe-birr.api"
            mock_settings.CBE_BIRR_MERCHANT_ID = "test_merchant"
            
            provider = CBEBirrProvider()
            assert provider.name == "cbe_birr"


@pytest.mark.unit
class TestPaymentFactory:
    """Tests for payment factory."""
    
    def test_get_payment_provider(self):
        """Test getting payment provider by method."""
        from infrastructure.payments.factory import get_payment_provider
        
        with patch('infrastructure.payments.factory.PaymentFactory.get_provider') as mock_get:
            mock_get.return_value = Mock()
            
            provider = get_payment_provider("chapa")
            assert provider is not None
    
    def test_register_provider(self):
        """Test registering a payment provider."""
        from infrastructure.payments.factory import PaymentFactory
        
        mock_provider = Mock()
        PaymentFactory.register_provider("test_provider", mock_provider)
        
        assert "test_provider" in PaymentFactory._providers


@pytest.mark.unit
class TestPaymentRequest:
    """Tests for payment request model."""
    
    def test_payment_request_creation(self):
        """Test creating a payment request."""
        from infrastructure.payments.base import PaymentRequest
        
        request = PaymentRequest(
            amount=Decimal("100.00"),
            currency="ETB",
            order_id=1,
            order_number="ORD-001",
            customer_name="Test Customer",
            customer_email="test@example.com",
            customer_phone="0912345678",
        )
        
        assert request.amount == Decimal("100.00")
        assert request.order_id == 1
        assert request.customer_name == "Test Customer"


@pytest.mark.unit
class TestPaymentResponse:
    """Tests for payment response model."""
    
    def test_payment_response_creation(self):
        """Test creating a payment response."""
        from infrastructure.payments.base import PaymentResponse
        from infrastructure.payments.base import PaymentStatus
        
        response = PaymentResponse(
            success=True,
            transaction_id="txn_123",
            status=PaymentStatus.PENDING,
            redirect_url="https://test.com/pay",
        )
        
        assert response.success is True
        assert response.transaction_id == "txn_123"
        assert response.status == PaymentStatus.PENDING


@pytest.mark.unit
class TestPaymentVerification:
    """Tests for payment verification model."""
    
    def test_payment_verification_creation(self):
        """Test creating a payment verification result."""
        from infrastructure.payments.base import PaymentVerification
        from infrastructure.payments.base import PaymentStatus
        
        verification = PaymentVerification(
            verified=True,
            transaction_id="txn_123",
            status=PaymentStatus.COMPLETED,
            amount=Decimal("100.00"),
        )
        
        assert verification.verified is True
        assert verification.transaction_id == "txn_123"
        assert verification.status == PaymentStatus.COMPLETED


@pytest.mark.unit
class TestPaymentVerifier:
    """Tests for payment verifier utility."""
    
    @pytest.mark.asyncio
    async def test_verify_payment(self):
        """Test payment verification."""
        from infrastructure.payments.payment_verifier import PaymentVerifier
        
        verifier = PaymentVerifier()
        
        with patch('infrastructure.payments.payment_verifier.get_payment_provider') as mock_get:
            mock_provider = AsyncMock()
            mock_provider.verify_payment.return_value = Mock(verified=True)
            mock_get.return_value = mock_provider
            
            result = await verifier.verify_payment("chapa", "txn_123")
            
            assert result.verified is True
    
    @pytest.mark.asyncio
    async def test_verify_webhook(self):
        """Test webhook verification."""
        from infrastructure.payments.payment_verifier import PaymentVerifier
        
        verifier = PaymentVerifier()
        
        with patch('infrastructure.payments.payment_verifier.get_payment_provider') as mock_get:
            mock_provider = AsyncMock()
            mock_provider.process_webhook.return_value = Mock(verified=True)
            mock_get.return_value = mock_provider
            
            result = await verifier.verify_webhook("chapa", {"data": "test"})
            
            assert result.verified is True


@pytest.mark.unit
class TestPaymentReconciliation:
    """Tests for payment reconciliation."""
    
    @pytest.mark.asyncio
    async def test_reconcile_payments(self):
        """Test payment reconciliation."""
        from infrastructure.payments.reconciliation import reconcile_payments
        from datetime import datetime, timedelta
        
        mock_db = Mock()
        start_date = datetime.utcnow() - timedelta(days=30)
        end_date = datetime.utcnow()
        
        with patch('infrastructure.payments.reconciliation.PaymentReconciliation') as mock_recon:
            mock_instance = AsyncMock()
            mock_recon.return_value = mock_instance
            mock_instance.generate_reconciliation_report.return_value = {"total_transactions": 0}
            
            result = await reconcile_payments(mock_db, start_date, end_date)
            
            assert "total_transactions" in result


@pytest.mark.unit
class TestPaymentProcessing:
    """Tests for payment processing function."""
    
    @pytest.mark.asyncio
    async def test_process_payment(self):
        """Test processing a payment."""
        from infrastructure.payments.factory import process_payment
        
        with patch('infrastructure.payments.factory.get_payment_provider') as mock_get:
            mock_provider = AsyncMock()
            mock_response = Mock(success=True, transaction_id="txn_123")
            mock_provider.initialize_payment.return_value = mock_response
            mock_get.return_value = mock_provider
            
            result = await process_payment(
                method="chapa",
                amount=Decimal("100.00"),
                order_id=1,
                order_number="ORD-001",
                customer_name="Test",
                customer_email="test@test.com",
                customer_phone="0912345678",
            )
            
            assert result.success is True
            assert result.transaction_id == "txn_123"


@pytest.mark.unit
class TestPaymentSplit:
    """Tests for split payment functionality."""
    
    @pytest.mark.asyncio
    async def test_create_split_payment(self):
        """Test creating a split payment."""
        from infrastructure.payments_advanced.split_payments import create_split_payment
        
        mock_db = Mock()
        vendor_splits = [
            {"vendor_id": 1, "amount": 50.00},
            {"vendor_id": 2, "amount": 50.00},
        ]
        
        with patch('infrastructure.payments_advanced.split_payments.SplitPaymentManager') as mock_manager:
            mock_instance = AsyncMock()
            mock_manager.return_value = mock_instance
            mock_instance.create_split_payment.return_value = Mock(status="pending")
            
            result = await create_split_payment(
                db=mock_db,
                order_id=1,
                order_number="ORD-001",
                customer_name="Test",
                customer_email="test@test.com",
                customer_phone="0912345678",
                vendor_splits=vendor_splits,
            )
            
            assert result is not None


@pytest.mark.unit
class TestEscrowService:
    """Tests for escrow service."""
    
    @pytest.mark.asyncio
    async def test_create_escrow(self):
        """Test creating an escrow transaction."""
        from infrastructure.payments_advanced.escrow_service import create_escrow
        from decimal import Decimal
        
        mock_db = Mock()
        
        with patch('infrastructure.payments_advanced.escrow_service.EscrowService') as mock_service:
            mock_instance = AsyncMock()
            mock_service.return_value = mock_instance
            mock_instance.create_escrow.return_value = Mock(escrow_id="ESC_123")
            
            result = await create_escrow(
                db=mock_db,
                order_id=1,
                order_number="ORD-001",
                buyer_id=100,
                seller_id=200,
                amount=Decimal("500.00"),
            )
            
            assert result is not None
            assert result.escrow_id == "ESC_123"


__all__ = [
    "TestPaymentProvider",
    "TestPaymentFactory",
    "TestPaymentRequest",
    "TestPaymentResponse",
    "TestPaymentVerification",
    "TestPaymentVerifier",
    "TestPaymentReconciliation",
    "TestPaymentProcessing",
    "TestPaymentSplit",
    "TestEscrowService",
]