# ============================
# WOLLOYEWA STORE BOT - SMS GATEWAY
# ============================
"""SMS notification service for Ethiopian and international providers."""

from typing import Optional, Dict, Any
import httpx

from infrastructure.notifications.base import (
    NotificationProvider,
    NotificationRequest,
    NotificationResponse,
    NotificationType,
    NotificationError,
)
from core.config import settings
from core.logger import logger


class SMSGateway(NotificationProvider):
    """
    SMS notification service.
    
    Supports:
    - Ethio Telecom SMS gateway
    - African's Talking
    - Twilio (fallback)
    """
    
    def __init__(self):
        self.provider = settings.SMS_PROVIDER
        self.api_key = settings.SMS_API_KEY
        self.sender_id = settings.SMS_SENDER_ID
        
        # Provider-specific configurations
        self._providers = {
            "ethio_telecom": self._send_via_ethio_telecom,
            "african_talking": self._send_via_african_talking,
            "twilio": self._send_via_twilio,
        }
    
    @property
    def name(self) -> str:
        return self.provider
    
    @property
    def notification_type(self) -> NotificationType:
        return NotificationType.SMS
    
    async def send(self, request: NotificationRequest) -> NotificationResponse:
        """
        Send an SMS.
        
        Args:
            request: Notification request
            
        Returns:
            Notification response
        """
        # Validate phone number
        phone = self._normalize_phone(request.to)
        if not phone:
            return NotificationResponse(
                success=False,
                error="Invalid phone number",
                status="failed",
            )
        
        # Get provider function
        send_func = self._providers.get(self.provider, self._send_via_african_talking)
        
        try:
            result = await send_func(phone, request.content or "")
            
            if result.get("success"):
                return NotificationResponse(
                    success=True,
                    message_id=result.get("message_id"),
                    status="sent",
                )
            else:
                return NotificationResponse(
                    success=False,
                    error=result.get("error", "Unknown error"),
                    status="failed",
                )
                
        except Exception as e:
            logger.error(f"SMS sending failed: {e}")
            return NotificationResponse(
                success=False,
                error=str(e),
                status="failed",
            )
    
    async def get_status(self, message_id: str) -> Dict[str, Any]:
        """Get SMS delivery status."""
        # Implement status checking based on provider
        return {"status": "unknown", "message_id": message_id}
    
    def _normalize_phone(self, phone: str) -> Optional[str]:
        """Normalize phone number to international format."""
        import re
        
        # Remove non-digit characters
        digits = re.sub(r'\D', '', phone)
        
        # Ethiopian phone numbers
        if digits.startswith("09") or digits.startswith("07"):
            if len(digits) == 10:
                return f"251{digits[1:]}"  # Convert to 2519XXXXXXXX
            elif len(digits) == 12 and digits.startswith("251"):
                return digits
        
        return None
    
    async def _send_via_ethio_telecom(self, phone: str, message: str) -> Dict[str, Any]:
        """
        Send SMS via Ethio Telecom gateway.
        
        Args:
            phone: Recipient phone number
            message: SMS content
            
        Returns:
            Result dictionary
        """
        # Ethio Telecom SMS API endpoint
        # This is a placeholder - actual API details would be provided by Ethio Telecom
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(
                    "https://api.ethiotelecom.et/sms/v1/send",
                    json={
                        "apiKey": self.api_key,
                        "senderId": self.sender_id,
                        "recipient": phone,
                        "message": message,
                    },
                )
                
                if response.status_code == 200:
                    data = response.json()
                    return {
                        "success": True,
                        "message_id": data.get("messageId"),
                    }
                else:
                    return {
                        "success": False,
                        "error": f"HTTP {response.status_code}",
                    }
                    
        except Exception as e:
            logger.error(f"Ethio Telecom SMS failed: {e}")
            return {"success": False, "error": str(e)}
    
    async def _send_via_african_talking(self, phone: str, message: str) -> Dict[str, Any]:
        """
        Send SMS via African's Talking gateway.
        
        Args:
            phone: Recipient phone number
            message: SMS content
            
        Returns:
            Result dictionary
        """
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(
                    "https://api.africastalking.com/version1/messaging",
                    headers={
                        "apiKey": self.api_key,
                        "Content-Type": "application/x-www-form-urlencoded",
                    },
                    data={
                        "username": "sandbox",
                        "to": phone,
                        "message": message,
                        "from": self.sender_id,
                    },
                )
                
                if response.status_code == 200:
                    data = response.json()
                    if data.get("SMSMessageData", {}).get("Recipients"):
                        return {
                            "success": True,
                            "message_id": data["SMSMessageData"]["Recipients"][0]["messageId"],
                        }
                
                return {"success": False, "error": "Failed to send"}
                
        except Exception as e:
            logger.error(f"African's Talking SMS failed: {e}")
            return {"success": False, "error": str(e)}
    
    async def _send_via_twilio(self, phone: str, message: str) -> Dict[str, Any]:
        """
        Send SMS via Twilio gateway.
        
        Args:
            phone: Recipient phone number
            message: SMS content
            
        Returns:
            Result dictionary
        """
        # Twilio integration would go here
        # Requires twilio SDK
        return {"success": False, "error": "Twilio not configured"}


# Global SMS gateway instance
_sms_gateway = SMSGateway()


async def send_sms(to: str, message: str) -> bool:
    """
    Send an SMS.
    
    Args:
        to: Recipient phone number
        message: SMS content
        
    Returns:
        True if sent successfully
    """
    request = NotificationRequest(
        type=NotificationType.SMS,
        to=to,
        content=message,
    )
    
    response = await _sms_gateway.send(request)
    return response.success


async def send_verification_code(phone: str, code: str) -> bool:
    """Send verification code via SMS."""
    message = f"Your Wolloyewa verification code is: {code}. Valid for 5 minutes."
    return await send_sms(phone, message)


async def send_order_update_sms(phone: str, order_number: str, status: str) -> bool:
    """Send order status update via SMS."""
    status_amharic = {
        "confirmed": "ተረጋግጧል",
        "shipped": "ተልኳል",
        "delivered": "ደርሷል",
        "cancelled": "ተሰርዟል",
    }
    
    status_text = status_amharic.get(status, status)
    message = f"Wolloyewa: ትዕዛዝ #{order_number} {status_text} ነው።"
    
    return await send_sms(phone, message)


__all__ = [
    "SMSGateway",
    "send_sms",
    "send_verification_code",
    "send_order_update_sms",
]