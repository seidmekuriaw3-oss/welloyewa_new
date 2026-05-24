# ============================
# WOLLOYEWA STORE BOT - TELEBIRR PAYMENT PROVIDER
# ============================
"""Telebirr payment gateway integration for Ethiopian mobile payments."""

import hashlib
import hmac
import json
import time
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


class TelebirrProvider(PaymentProvider):
    """
    Telebirr payment gateway provider.
    
    Telebirr is Ethiopian Telecom's mobile money service.
    Supports QR code payments and direct mobile payments.
    
    Documentation: https://api.ethiotelecom.et/telebirr
    """
    
    def __init__(self):
        self.api_url = settings.TELEBIRR_API_URL
        self.app_id = settings.TELEBIRR_APP_ID
        self.app_key = settings.TELEBIRR_APP_KEY
        self.short_code = settings.TELEBIRR_SHORT_CODE
    
    @property
    def name(self) -> str:
        return "telebirr"
    
    async def _get_access_token(self) -> Optional[str]:
        """Get access token from Telebirr API."""
        try:
            payload = {
                "appId": self.app_id,
                "appKey": self.app_key,
            }
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{self.api_url}/auth/token",
                    json=payload,
                )
                
                if response.status_code == 200:
                    data = response.json()
                    return data.get("access_token")
                else:
                    logger.error(f"Telebirr token error: {response.text}")
                    return None
                    
        except Exception as e:
            logger.error(f"Failed to get Telebirr token: {e}")
            return None
    
    async def _make_request(
        self,
        endpoint: str,
        data: Dict,
        method: str = "POST",
    ) -> Dict:
        """Make authenticated request to Telebirr API."""
        token = await self._get_access_token()
        if not token:
            raise PaymentError("Failed to authenticate with Telebirr")
        
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                url = f"{self.api_url}/{endpoint}"
                
                if method.upper() == "GET":
                    response = await client.get(url, headers=headers)
                else:
                    response = await client.post(url, json=data, headers=headers)
                
                response.raise_for_status()
                return response.json()
                
            except httpx.HTTPStatusError as e:
                logger.error(f"Telebirr API error: {e.response.text}")
                raise PaymentError(f"Telebirr error: {e.response.status_code}")
            except Exception as e:
                logger.error(f"Telebirr request failed: {e}")
                raise PaymentError(f"Failed to connect to Telebirr: {e}")
    
    async def initialize_payment(self, request: PaymentRequest) -> PaymentResponse:
        """
        Initialize Telebirr payment.
        
        Args:
            request: Payment request data
            
        Returns:
            Payment response with QR code or payment URL
        """
        try:
            # Prepare payload
            timestamp = str(int(time.time() * 1000))
            
            payload = {
                "appId": self.app_id,
                "appKey": self.app_key,
                "shortCode": self.short_code,
                "outTradeNo": f"ORDER_{request.order_number}",
                "subject": request.description or f"Order {request.order_number}",
                "totalAmount": str(float(request.amount)),
                "timeoutExpress": "30m",
                "notifyUrl": request.webhook_url,
                "returnUrl": request.callback_url,
            }
            
            # Add customer info if available
            if request.customer_phone:
                payload["buyerPhone"] = request.customer_phone
            
            # Generate signature
            payload["sign"] = self._generate_signature(payload)
            
            # Make API call
            result = await self._make_request("v1/payment/create", payload)
            
            if result.get("code") == "10000":
                return PaymentResponse(
                    success=True,
                    transaction_id=result.get("outTradeNo"),
                    status=PaymentStatus.PENDING,
                    payment_url=result.get("qrCodeUrl"),
                    reference=result.get("outTradeNo"),
                    raw_response=result,
                )
            else:
                return PaymentResponse(
                    success=False,
                    message=result.get("msg", "Payment initialization failed"),
                    status=PaymentStatus.FAILED,
                    raw_response=result,
                )
                
        except Exception as e:
            logger.error(f"Telebirr payment initialization failed: {e}")
            return PaymentResponse(
                success=False,
                message=str(e),
                status=PaymentStatus.FAILED,
            )
    
    async def verify_payment(self, transaction_id: str) -> PaymentVerification:
        """
        Verify Telebirr payment status.
        
        Args:
            transaction_id: Transaction reference (outTradeNo)
            
        Returns:
            Payment verification result
        """
        try:
            payload = {
                "appId": self.app_id,
                "appKey": self.app_key,
                "outTradeNo": transaction_id,
            }
            
            payload["sign"] = self._generate_signature(payload)
            
            result = await self._make_request("v1/payment/query", payload)
            
            if result.get("code") == "10000":
                data = result.get("data", {})
                status = self._map_status(data.get("tradeStatus"))
                
                return PaymentVerification(
                    verified=status == PaymentStatus.COMPLETED,
                    transaction_id=transaction_id,
                    status=status,
                    amount=Decimal(str(data.get("totalAmount", 0))),
                    customer_phone=data.get("buyerPhone"),
                    raw_response=result,
                )
            else:
                return PaymentVerification(
                    verified=False,
                    transaction_id=transaction_id,
                    status=PaymentStatus.FAILED,
                    message=result.get("msg", "Verification failed"),
                    raw_response=result,
                )
                
        except Exception as e:
            logger.error(f"Telebirr payment verification failed: {e}")
            return PaymentVerification(
                verified=False,
                transaction_id=transaction_id,
                status=PaymentStatus.FAILED,
                message=str(e),
            )
    
    async def process_webhook(self, payload: Dict[str, Any]) -> PaymentVerification:
        """
        Process Telebirr webhook notification.
        
        Args:
            payload: Webhook payload
            
        Returns:
            Payment verification result
        """
        # Verify signature
        if not self._verify_signature(payload):
            logger.warning("Invalid webhook signature from Telebirr")
            return PaymentVerification(
                verified=False,
                status=PaymentStatus.FAILED,
                message="Invalid signature",
            )
        
        transaction_id = payload.get("outTradeNo")
        status = self._map_status(payload.get("tradeStatus"))
        
        return PaymentVerification(
            verified=status == PaymentStatus.COMPLETED,
            transaction_id=transaction_id,
            status=status,
            amount=Decimal(str(payload.get("totalAmount", 0))),
            customer_phone=payload.get("buyerPhone"),
            raw_response=payload,
        )
    
    async def refund_payment(
        self,
        transaction_id: str,
        amount: Optional[Decimal] = None,
        reason: Optional[str] = None,
    ) -> bool:
        """
        Refund a Telebirr payment.
        
        Args:
            transaction_id: Transaction reference
            amount: Amount to refund (Telebirr supports full refund only)
            reason: Refund reason
            
        Returns:
            True if refund successful
        """
        try:
            payload = {
                "appId": self.app_id,
                "appKey": self.app_key,
                "outTradeNo": transaction_id,
                "refundReason": reason or "Customer request",
            }
            
            payload["sign"] = self._generate_signature(payload)
            
            result = await self._make_request("v1/payment/refund", payload)
            
            return result.get("code") == "10000"
            
        except Exception as e:
            logger.error(f"Telebirr refund failed: {e}")
            return False
    
    def _generate_signature(self, data: Dict[str, Any]) -> str:
        """Generate HMAC-SHA256 signature for Telebirr."""
        # Sort keys alphabetically
        sorted_keys = sorted(data.keys())
        sign_string = "&".join([f"{k}={data[k]}" for k in sorted_keys if data[k]])
        
        signature = hmac.new(
            self.app_key.encode(),
            sign_string.encode(),
            hashlib.sha256,
        ).hexdigest()
        
        return signature
    
    def _verify_signature(self, payload: Dict[str, Any]) -> bool:
        """Verify webhook signature."""
        signature = payload.get("sign")
        if not signature:
            return False
        
        # Remove signature from payload
        payload_copy = {k: v for k, v in payload.items() if k != "sign"}
        expected = self._generate_signature(payload_copy)
        
        return hmac.compare_digest(expected, signature)
    
    def _map_status(self, telebirr_status: Optional[str]) -> PaymentStatus:
        """Map Telebirr status to internal status."""
        status_map = {
            "TRADE_SUCCESS": PaymentStatus.COMPLETED,
            "TRADE_PENDING": PaymentStatus.PENDING,
            "TRADE_FAILED": PaymentStatus.FAILED,
            "TRADE_REFUNDED": PaymentStatus.REFUNDED,
            "TRADE_CLOSED": PaymentStatus.CANCELLED,
        }
        return status_map.get(telebirr_status, PaymentStatus.PENDING)


__all__ = ["TelebirrProvider"]