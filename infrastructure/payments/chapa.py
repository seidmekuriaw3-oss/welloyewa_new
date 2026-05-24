# ============================
# WOLLOYEWA STORE BOT - CHAPA PAYMENT PROVIDER
# ============================
"""Chapa payment gateway integration for Ethiopian payments."""

import hashlib
import hmac
import json
from decimal import Decimal
from typing import Dict, Any, Optional
import httpx

from infrastructure.payments.base import (
    PaymentProvider,
    PaymentRequest,
    PaymentResponse,
    PaymentVerification,
    PaymentStatus,
    PaymentError,
)
from core.config import settings
from core.logger import logger


class ChapaProvider(PaymentProvider):
    """
    Chapa payment gateway provider.
    
    Chapa is an Ethiopian payment gateway supporting:
    - Telebirr
    - CBE Birr
    - Card payments
    - Bank transfers
    
    Documentation: https://docs.chapa.co/
    """
    
    def __init__(self):
        self.api_url = settings.CHAPA_API_URL
        self.secret_key = settings.CHAPA_SECRET_KEY
        self.webhook_secret = settings.CHAPA_WEBHOOK_SECRET
    
    @property
    def name(self) -> str:
        return "chapa"
    
    async def _make_request(
        self,
        endpoint: str,
        method: str = "POST",
        data: Optional[Dict] = None,
    ) -> Dict:
        """Make HTTP request to Chapa API."""
        url = f"{self.api_url}/{endpoint}"
        headers = {
            "Authorization": f"Bearer {self.secret_key}",
            "Content-Type": "application/json",
        }
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                if method.upper() == "GET":
                    response = await client.get(url, headers=headers)
                else:
                    response = await client.post(url, json=data, headers=headers)
                
                response.raise_for_status()
                return response.json()
                
            except httpx.HTTPStatusError as e:
                logger.error(f"Chapa API error: {e.response.text}")
                raise PaymentError(f"Payment gateway error: {e.response.status_code}")
            except Exception as e:
                logger.error(f"Chapa request failed: {e}")
                raise PaymentError(f"Failed to connect to payment gateway: {e}")
    
    async def initialize_payment(self, request: PaymentRequest) -> PaymentResponse:
        """
        Initialize payment with Chapa.
        
        Args:
            request: Payment request data
            
        Returns:
            Payment response with checkout URL
        """
        try:
            # Prepare payload
            payload = {
                "amount": float(request.amount),
                "currency": request.currency,
                "email": request.customer_email,
                "first_name": request.customer_name.split()[0] if request.customer_name else "",
                "last_name": " ".join(request.customer_name.split()[1:]) if request.customer_name else "",
                "phone_number": request.customer_phone,
                "tx_ref": f"ORDER_{request.order_number}",
                "callback_url": request.callback_url,
                "return_url": request.callback_url,
                "customization": {
                    "title": f"Order {request.order_number}",
                    "description": request.description or f"Payment for order {request.order_number}",
                },
            }
            
            # Add metadata
            if request.metadata:
                payload["meta"] = request.metadata
            
            # Make API call
            result = await self._make_request("transaction/initialize", data=payload)
            
            if result.get("status") == "success":
                return PaymentResponse(
                    success=True,
                    transaction_id=result.get("data", {}).get("tx_ref"),
                    status=PaymentStatus.PENDING,
                    redirect_url=result.get("data", {}).get("checkout_url"),
                    payment_url=result.get("data", {}).get("checkout_url"),
                    reference=result.get("data", {}).get("tx_ref"),
                    raw_response=result,
                )
            else:
                return PaymentResponse(
                    success=False,
                    message=result.get("message", "Payment initialization failed"),
                    raw_response=result,
                )
                
        except Exception as e:
            logger.error(f"Chapa payment initialization failed: {e}")
            return PaymentResponse(
                success=False,
                message=str(e),
                status=PaymentStatus.FAILED,
            )
    
    async def verify_payment(self, transaction_id: str) -> PaymentVerification:
        """
        Verify payment status with Chapa.
        
        Args:
            transaction_id: Transaction reference
            
        Returns:
            Payment verification result
        """
        try:
            result = await self._make_request(f"transaction/verify/{transaction_id}", method="GET")
            
            if result.get("status") == "success":
                data = result.get("data", {})
                status = self._map_status(data.get("status"))
                
                return PaymentVerification(
                    verified=status == PaymentStatus.COMPLETED,
                    transaction_id=transaction_id,
                    status=status,
                    amount=Decimal(str(data.get("amount", 0))),
                    currency=data.get("currency", "ETB"),
                    customer_email=data.get("email"),
                    customer_phone=data.get("phone_number"),
                    metadata=data.get("meta", {}),
                    raw_response=result,
                )
            else:
                return PaymentVerification(
                    verified=False,
                    transaction_id=transaction_id,
                    status=PaymentStatus.FAILED,
                    message=result.get("message", "Verification failed"),
                    raw_response=result,
                )
                
        except Exception as e:
            logger.error(f"Chapa payment verification failed: {e}")
            return PaymentVerification(
                verified=False,
                transaction_id=transaction_id,
                status=PaymentStatus.FAILED,
                message=str(e),
            )
    
    async def process_webhook(self, payload: Dict[str, Any]) -> PaymentVerification:
        """
        Process Chapa webhook notification.
        
        Args:
            payload: Webhook payload
            
        Returns:
            Payment verification result
        """
        # Verify webhook signature
        signature = payload.get("signature")
        if signature:
            if not self._verify_signature(payload, signature):
                logger.warning("Invalid webhook signature from Chapa")
                return PaymentVerification(
                    verified=False,
                    status=PaymentStatus.FAILED,
                    message="Invalid signature",
                )
        
        # Extract data
        data = payload.get("data", {})
        transaction_id = data.get("tx_ref")
        status = self._map_status(data.get("status"))
        
        return PaymentVerification(
            verified=status == PaymentStatus.COMPLETED,
            transaction_id=transaction_id,
            status=status,
            amount=Decimal(str(data.get("amount", 0))),
            currency=data.get("currency", "ETB"),
            customer_email=data.get("email"),
            customer_phone=data.get("phone_number"),
            metadata=data.get("meta", {}),
            raw_response=payload,
        )
    
    async def refund_payment(
        self,
        transaction_id: str,
        amount: Optional[Decimal] = None,
        reason: Optional[str] = None,
    ) -> bool:
        """
        Refund a payment through Chapa.
        
        Args:
            transaction_id: Transaction reference
            amount: Amount to refund (None for full)
            reason: Refund reason
            
        Returns:
            True if refund successful
        """
        try:
            payload = {
                "tx_ref": transaction_id,
                "reason": reason or "Customer request",
            }
            
            if amount:
                payload["amount"] = float(amount)
            
            result = await self._make_request("transaction/refund", data=payload)
            
            return result.get("status") == "success"
            
        except Exception as e:
            logger.error(f"Chapa refund failed: {e}")
            return False
    
    def _map_status(self, chapa_status: Optional[str]) -> PaymentStatus:
        """Map Chapa status to internal status."""
        status_map = {
            "success": PaymentStatus.COMPLETED,
            "pending": PaymentStatus.PENDING,
            "failed": PaymentStatus.FAILED,
            "refunded": PaymentStatus.REFUNDED,
            "cancelled": PaymentStatus.CANCELLED,
        }
        return status_map.get(chapa_status, PaymentStatus.PENDING)
    
    def _verify_signature(self, payload: Dict, signature: str) -> bool:
        """Verify webhook signature."""
        if not self.webhook_secret:
            return True
        
        # Remove signature from payload for verification
        payload_copy = {k: v for k, v in payload.items() if k != "signature"}
        payload_json = json.dumps(payload_copy, sort_keys=True)
        
        expected = hmac.new(
            self.webhook_secret.encode(),
            payload_json.encode(),
            hashlib.sha256,
        ).hexdigest()
        
        return hmac.compare_digest(expected, signature)


__all__ = ["ChapaProvider"]