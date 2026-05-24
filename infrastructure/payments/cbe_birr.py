# ============================
# WOLLOYEWA STORE BOT - CBE BIRR PAYMENT PROVIDER
# ============================
"""Commercial Bank of Ethiopia (CBE) Birr payment gateway integration."""

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


class CBEBirrProvider(PaymentProvider):
    """
    CBE Birr payment gateway provider.
    
    CBE Birr is Commercial Bank of Ethiopia's digital payment solution.
    Supports merchant payments and fund transfers.
    
    Documentation: https://cbe-birr.api (Internal CBE documentation)
    """
    
    def __init__(self):
        self.api_url = settings.CBE_BIRR_API_URL
        self.merchant_id = settings.CBE_BIRR_MERCHANT_ID
        self.terminal_id = settings.CBE_BIRR_TERMINAL_ID
        self.secret_key = settings.CBE_BIRR_SECRET_KEY
    
    @property
    def name(self) -> str:
        return "cbe_birr"
    
    async def _get_session_token(self) -> Optional[str]:
        """Get session token from CBE Birr API."""
        try:
            payload = {
                "merchantId": self.merchant_id,
                "terminalId": self.terminal_id,
            }
            
            # Generate signature
            timestamp = str(int(time.time()))
            payload["timestamp"] = timestamp
            payload["signature"] = self._generate_signature(payload, timestamp)
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{self.api_url}/api/v1/auth/token",
                    json=payload,
                )
                
                if response.status_code == 200:
                    data = response.json()
                    if data.get("responseCode") == "0000":
                        return data.get("sessionToken")
                    else:
                        logger.error(f"CBE Birr token error: {data.get('responseMessage')}")
                        return None
                else:
                    logger.error(f"CBE Birr token HTTP error: {response.status_code}")
                    return None
                    
        except Exception as e:
            logger.error(f"Failed to get CBE Birr token: {e}")
            return None
    
    async def _make_request(
        self,
        endpoint: str,
        data: Dict,
        method: str = "POST",
    ) -> Dict:
        """Make authenticated request to CBE Birr API."""
        token = await self._get_session_token()
        if not token:
            raise PaymentError("Failed to authenticate with CBE Birr")
        
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "Merchant-Id": self.merchant_id,
            "Terminal-Id": self.terminal_id,
        }
        
        # Add timestamp and signature
        data["timestamp"] = str(int(time.time()))
        data["signature"] = self._generate_signature(data, data["timestamp"])
        
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
                logger.error(f"CBE Birr API error: {e.response.text}")
                raise PaymentError(f"CBE Birr error: {e.response.status_code}")
            except Exception as e:
                logger.error(f"CBE Birr request failed: {e}")
                raise PaymentError(f"Failed to connect to CBE Birr: {e}")
    
    async def initialize_payment(self, request: PaymentRequest) -> PaymentResponse:
        """
        Initialize CBE Birr payment.
        
        Args:
            request: Payment request data
            
        Returns:
            Payment response with QR code or payment reference
        """
        try:
            payload = {
                "merchantId": self.merchant_id,
                "terminalId": self.terminal_id,
                "orderId": f"ORD_{request.order_number}",
                "amount": str(float(request.amount)),
                "currencyCode": "ETB",
                "description": request.description or f"Order {request.order_number}",
                "customerName": request.customer_name,
                "customerPhone": request.customer_phone,
                "customerEmail": request.customer_email,
                "notifyUrl": request.webhook_url,
                "returnUrl": request.callback_url,
            }
            
            result = await self._make_request("api/v1/payment/initiate", payload)
            
            if result.get("responseCode") == "0000":
                data = result.get("data", {})
                return PaymentResponse(
                    success=True,
                    transaction_id=data.get("transactionId"),
                    status=PaymentStatus.PENDING,
                    payment_url=data.get("paymentUrl"),
                    reference=data.get("reference"),
                    raw_response=result,
                )
            else:
                return PaymentResponse(
                    success=False,
                    message=result.get("responseMessage", "Payment initialization failed"),
                    status=PaymentStatus.FAILED,
                    raw_response=result,
                )
                
        except Exception as e:
            logger.error(f"CBE Birr payment initialization failed: {e}")
            return PaymentResponse(
                success=False,
                message=str(e),
                status=PaymentStatus.FAILED,
            )
    
    async def verify_payment(self, transaction_id: str) -> PaymentVerification:
        """
        Verify CBE Birr payment status.
        
        Args:
            transaction_id: Transaction ID
            
        Returns:
            Payment verification result
        """
        try:
            payload = {
                "merchantId": self.merchant_id,
                "terminalId": self.terminal_id,
                "transactionId": transaction_id,
            }
            
            result = await self._make_request("api/v1/payment/status", payload)
            
            if result.get("responseCode") == "0000":
                data = result.get("data", {})
                status = self._map_status(data.get("transactionStatus"))
                
                return PaymentVerification(
                    verified=status == PaymentStatus.COMPLETED,
                    transaction_id=transaction_id,
                    status=status,
                    amount=Decimal(str(data.get("amount", 0))),
                    customer_phone=data.get("customerPhone"),
                    raw_response=result,
                )
            else:
                return PaymentVerification(
                    verified=False,
                    transaction_id=transaction_id,
                    status=PaymentStatus.FAILED,
                    message=result.get("responseMessage", "Verification failed"),
                    raw_response=result,
                )
                
        except Exception as e:
            logger.error(f"CBE Birr payment verification failed: {e}")
            return PaymentVerification(
                verified=False,
                transaction_id=transaction_id,
                status=PaymentStatus.FAILED,
                message=str(e),
            )
    
    async def process_webhook(self, payload: Dict[str, Any]) -> PaymentVerification:
        """
        Process CBE Birr webhook notification.
        
        Args:
            payload: Webhook payload
            
        Returns:
            Payment verification result
        """
        # Verify signature
        if not self._verify_signature(payload):
            logger.warning("Invalid webhook signature from CBE Birr")
            return PaymentVerification(
                verified=False,
                status=PaymentStatus.FAILED,
                message="Invalid signature",
            )
        
        transaction_id = payload.get("transactionId")
        status = self._map_status(payload.get("transactionStatus"))
        
        return PaymentVerification(
            verified=status == PaymentStatus.COMPLETED,
            transaction_id=transaction_id,
            status=status,
            amount=Decimal(str(payload.get("amount", 0))),
            customer_phone=payload.get("customerPhone"),
            raw_response=payload,
        )
    
    async def refund_payment(
        self,
        transaction_id: str,
        amount: Optional[Decimal] = None,
        reason: Optional[str] = None,
    ) -> bool:
        """
        Refund a CBE Birr payment.
        
        Args:
            transaction_id: Transaction ID
            amount: Amount to refund (None for full)
            reason: Refund reason
            
        Returns:
            True if refund successful
        """
        try:
            payload = {
                "merchantId": self.merchant_id,
                "terminalId": self.terminal_id,
                "transactionId": transaction_id,
                "refundReason": reason or "Customer request",
            }
            
            if amount:
                payload["refundAmount"] = str(float(amount))
            
            result = await self._make_request("api/v1/payment/refund", payload)
            
            return result.get("responseCode") == "0000"
            
        except Exception as e:
            logger.error(f"CBE Birr refund failed: {e}")
            return False
    
    def _generate_signature(self, data: Dict[str, Any], timestamp: str) -> str:
        """Generate HMAC-SHA256 signature for CBE Birr."""
        # Create string to sign
        sign_data = f"{self.merchant_id}{self.terminal_id}{timestamp}"
        for key in sorted(data.keys()):
            if key not in ["signature", "timestamp"] and data[key]:
                sign_data += str(data[key])
        
        signature = hmac.new(
            self.secret_key.encode(),
            sign_data.encode(),
            hashlib.sha256,
        ).hexdigest()
        
        return signature
    
    def _verify_signature(self, payload: Dict[str, Any]) -> bool:
        """Verify webhook signature."""
        signature = payload.get("signature")
        timestamp = payload.get("timestamp")
        
        if not signature or not timestamp:
            return False
        
        # Remove signature from payload
        payload_copy = {k: v for k, v in payload.items() if k != "signature"}
        expected = self._generate_signature(payload_copy, timestamp)
        
        return hmac.compare_digest(expected, signature)
    
    def _map_status(self, cbe_status: Optional[str]) -> PaymentStatus:
        """Map CBE Birr status to internal status."""
        status_map = {
            "SUCCESS": PaymentStatus.COMPLETED,
            "PENDING": PaymentStatus.PENDING,
            "PROCESSING": PaymentStatus.PROCESSING,
            "FAILED": PaymentStatus.FAILED,
            "REFUNDED": PaymentStatus.REFUNDED,
            "CANCELLED": PaymentStatus.CANCELLED,
        }
        return status_map.get(cbe_status, PaymentStatus.PENDING)


__all__ = ["CBEBirrProvider"]