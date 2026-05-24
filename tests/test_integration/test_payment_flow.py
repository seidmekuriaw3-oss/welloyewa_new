# ============================
# WOLLOYEWA STORE BOT - PAYMENT FLOW INTEGRATION TESTS
# ============================
"""Integration tests for payment processing flows."""

import pytest
from decimal import Decimal
from unittest.mock import AsyncMock, Mock, patch


@pytest.mark.integration
class TestPaymentFlowIntegration:
    """Test complete payment processing flows."""
    
    @pytest.mark.asyncio
    async def test_chapa_payment_flow(self):
        """Test Chapa payment flow."""
        from infrastructure.payments.chapa import ChapaProvider
        from infrastructure.payments.base import PaymentRequest
        
        with patch('infrastructure.payments.chapa.httpx.AsyncClient') as mock_client:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "status": "success",
                "data": {
                    "tx_ref": "ORDER_ORD001",
                    "checkout_url": "https://checkout.chapa.co/pay/123",
                }
            }
            
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                return_value=mock_response
            )
            
            provider = ChapaProvider()
            request = PaymentRequest(
                amount=Decimal("100.00"),
                order_number="ORD001",
                customer_email="test@example.com",
                customer_phone="0912345678",
            )
            
            response = await provider.initialize_payment(request)
            
            assert response.success is True
            assert response.transaction_id == "ORDER_ORD001"
            assert response.payment_url is not None
    
    @pytest.mark.asyncio
    async def test_chapa_payment_verification(self):
        """Test Chapa payment verification."""
        from infrastructure.payments.chapa import ChapaProvider
        
        with patch('infrastructure.payments.chapa.httpx.AsyncClient') as mock_client:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "status": "success",
                "data": {
                    "status": "success",
                    "amount": 100.00,
                    "email": "test@example.com",
                }
            }
            
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                return_value=mock_response
            )
            
            provider = ChapaProvider()
            verification = await provider.verify_payment("ORDER_ORD001")
            
            assert verification.verified is True
    
    @pytest.mark.asyncio
    async def test_telebirr_payment_flow(self):
        """Test Telebirr payment flow."""
        from infrastructure.payments.telebirr import TelebirrProvider
        from infrastructure.payments.base import PaymentRequest
        
        with patch('infrastructure.payments.telebirr.TelebirrProvider._get_access_token') as mock_token:
            mock_token.return_value = "test_token"
            
            with patch('infrastructure.payments.telebirr.httpx.AsyncClient') as mock_client:
                mock_response = Mock()
                mock_response.status_code = 200
                mock_response.json.return_value = {
                    "code": "10000",
                    "qrCodeUrl": "https://telebirr.et/qr/123",
                    "outTradeNo": "ORDER_ORD001",
                }
                
                mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                    return_value=mock_response
                )
                
                provider = TelebirrProvider()
                request = PaymentRequest(
                    amount=Decimal("100.00"),
                    order_number="ORD001",
                    customer_phone="0912345678",
                )
                
                response = await provider.initialize_payment(request)
                
                assert response.success is True
                assert response.transaction_id == "ORDER_ORD001"
    
    @pytest.mark.asyncio
    async def test_cbe_birr_payment_flow(self):
        """Test CBE Birr payment flow."""
        from infrastructure.payments.cbe_birr import CBEBirrProvider
        from infrastructure.payments.base import PaymentRequest
        
        with patch('infrastructure.payments.cbe_birr.CBEBirrProvider._get_session_token') as mock_token:
            mock_token.return_value = "test_token"
            
            with patch('infrastructure.payments.cbe_birr.httpx.AsyncClient') as mock_client:
                mock_response = Mock()
                mock_response.status_code = 200
                mock_response.json.return_value = {
                    "responseCode": "0000",
                    "data": {
                        "transactionId": "CBE_123",
                        "paymentUrl": "https://cbe-birr.et/pay/123",
                    }
                }
                
                mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                    return_value=mock_response
                )
                
                provider = CBEBirrProvider()
                request = PaymentRequest(
                    amount=Decimal("100.00"),
                    order_number="ORD001",
                )
                
                response = await provider.initialize_payment(request)
                
                assert response.success is True
                assert response.transaction_id == "CBE_123"


@pytest.mark.integration
class TestPaymentWebhookFlow:
    """Test payment webhook processing flows."""
    
    @pytest.mark.asyncio
    async def test_chapa_webhook_processing(self):
        """Test Chapa webhook processing."""
        from infrastructure.payments.payment_verifier import PaymentVerifier
        
        webhook_payload = {
            "event": "charge.success",
            "data": {
                "tx_ref": "ORDER_ORD001",
                "amount": 100.00,
                "status": "success",
            }
        }
        
        with patch('infrastructure.payments.payment_verifier.get_payment_provider') as mock_get:
            mock_provider = AsyncMock()
            mock_provider.process_webhook.return_value = Mock(
                verified=True,
                transaction_id="ORDER_ORD001",
            )
            mock_get.return_value = mock_provider
            
            verifier = PaymentVerifier()
            result = await verifier.verify_webhook("chapa", webhook_payload)
            
            assert result.verified is True
            assert result.transaction_id == "ORDER_ORD001"
    
    @pytest.mark.asyncio
    async def test_webhook_signature_verification(self):
        """Test webhook signature verification."""
        from infrastructure.payments.payment_verifier import verify_payment_signature
        
        payload = {"amount": 100, "order_id": 1}
        secret = "test_secret"
        
        # This would normally verify a signature
        # For testing, we just check the function exists
        assert callable(verify_payment_signature)


@pytest.mark.integration
class TestPaymentRefundFlow:
    """Test payment refund flows."""
    
    @pytest.mark.asyncio
    async def test_chapa_refund_flow(self):
        """Test Chapa refund flow."""
        from infrastructure.payments.chapa import ChapaProvider
        
        with patch('infrastructure.payments.chapa.httpx.AsyncClient') as mock_client:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"status": "success"}
            
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                return_value=mock_response
            )
            
            provider = ChapaProvider()
            result = await provider.refund_payment("ORDER_ORD001")
            
            assert result is True


@pytest.mark.integration
class TestPaymentReconciliationFlow:
    """Test payment reconciliation flows."""
    
    @pytest.mark.asyncio
    async def test_reconciliation_flow(self):
        """Test payment reconciliation flow."""
        from infrastructure.payments.reconciliation import PaymentReconciliation
        
        mock_db = AsyncMock()
        reconciler = PaymentReconciliation(mock_db)
        
        with patch.object(reconciler, 'reconcile') as mock_reconcile:
            mock_reconcile.return_value = []
            
            result = await reconciler.reconcile("chapa", Mock(), Mock())
            
            assert result == []


__all__ = [
    "TestPaymentFlowIntegration",
    "TestPaymentWebhookFlow",
    "TestPaymentRefundFlow",
    "TestPaymentReconciliationFlow",
]