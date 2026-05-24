# ============================
# WOLLOYEWA STORE BOT - QR SCANNER INTEGRATION
# ============================
"""QR code generation and scanning for payments, products, and authentication."""

import json
import qrcode
from io import BytesIO
from enum import Enum
from typing import Dict, Any, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime

from core.logger import logger


class QRCodeType(str, Enum):
    """QR code data types."""
    PAYMENT = "payment"
    PRODUCT = "product"
    ORDER = "order"
    AUTH = "auth"
    STORE = "store"
    PROMOTION = "promotion"
    CONTACT = "contact"


@dataclass
class QRCodeData:
    """QR code data structure."""
    
    qr_type: QRCodeType
    data: Dict[str, Any]
    version: str = "1.0"
    created_at: datetime = field(default_factory=datetime.utcnow)
    
    def to_json(self) -> str:
        """Convert to JSON string."""
        return json.dumps({
            "type": self.qr_type.value,
            "version": self.version,
            "data": self.data,
            "created_at": self.created_at.isoformat(),
        })
    
    @classmethod
    def from_json(cls, json_str: str) -> "QRCodeData":
        """Create from JSON string."""
        data = json.loads(json_str)
        return cls(
            qr_type=QRCodeType(data["type"]),
            data=data["data"],
            version=data.get("version", "1.0"),
            created_at=datetime.fromisoformat(data["created_at"]),
        )


@dataclass
class QRPaymentData:
    """Payment QR code data."""
    
    order_id: int
    order_number: str
    amount: float
    merchant_id: str
    merchant_name: str
    currency: str = "ETB"
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "order_id": self.order_id,
            "order_number": self.order_number,
            "amount": self.amount,
            "merchant_id": self.merchant_id,
            "merchant_name": self.merchant_name,
            "currency": self.currency,
        }


@dataclass
class QRProductData:
    """Product QR code data."""
    
    product_id: int
    product_name: str
    price: float
    vendor_id: int
    vendor_name: str
    currency: str = "ETB"
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "product_id": self.product_id,
            "product_name": self.product_name,
            "price": self.price,
            "vendor_id": self.vendor_id,
            "vendor_name": self.vendor_name,
            "currency": self.currency,
        }


class QRScannerIntegration:
    """
    QR code integration for mobile apps.
    
    Features:
    - Generate QR codes for various use cases
    - Parse and validate QR codes
    - Support for payment QR codes
    - Product QR codes
    - Authentication QR codes
    """
    
    def __init__(self):
        pass
    
    async def generate_qr_code(
        self,
        qr_type: QRCodeType,
        data: Dict[str, Any],
        size: int = 300,
        border: int = 2,
    ) -> bytes:
        """
        Generate QR code as image.
        
        Args:
            qr_type: Type of QR code
            data: Data to encode
            size: Image size in pixels
            border: Border size (boxes)
            
        Returns:
            PNG image bytes
        """
        qr_data = QRCodeData(qr_type=qr_type, data=data)
        qr_json = qr_data.to_json()
        
        # Create QR code
        qr = qrcode.QRCode(
            version=None,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=size // 30,
            border=border,
        )
        qr.add_data(qr_json)
        qr.make(fit=True)
        
        # Generate image
        img = qr.make_image(fill_color="black", back_color="white")
        
        # Convert to bytes
        buffer = BytesIO()
        img.save(buffer, format="PNG")
        
        logger.info(f"Generated QR code for type: {qr_type.value}")
        return buffer.getvalue()
    
    async def scan_qr_code(self, image_data: bytes) -> Optional[QRCodeData]:
        """
        Scan QR code from image.
        
        Args:
            image_data: QR code image bytes
            
        Returns:
            Decoded QR code data or None
        """
        try:
            from PIL import Image
            import pyzbar.pyzbar as pyzbar
            
            # Open image
            img = Image.open(BytesIO(image_data))
            
            # Decode QR code
            decoded = pyzbar.decode(img)
            
            if not decoded:
                logger.warning("No QR code found in image")
                return None
            
            # Parse data
            qr_data_str = decoded[0].data.decode("utf-8")
            qr_data = QRCodeData.from_json(qr_data_str)
            
            logger.info(f"Scanned QR code of type: {qr_data.qr_type.value}")
            return qr_data
            
        except ImportError:
            logger.warning("pyzbar not installed. QR scanning disabled.")
            return None
        except Exception as e:
            logger.error(f"QR code scanning failed: {e}")
            return None
    
    async def decode_qr_data(self, qr_data: QRCodeData) -> Dict[str, Any]:
        """
        Decode and validate QR code data.
        
        Args:
            qr_data: QR code data
            
        Returns:
            Decoded and validated data
        """
        if qr_data.qr_type == QRCodeType.PAYMENT:
            return QRPaymentData(**qr_data.data).to_dict()
        elif qr_data.qr_type == QRCodeType.PRODUCT:
            return QRProductData(**qr_data.data).to_dict()
        elif qr_data.qr_type == QRCodeType.ORDER:
            return {
                "order_id": qr_data.data.get("order_id"),
                "order_number": qr_data.data.get("order_number"),
                "status": qr_data.data.get("status"),
            }
        elif qr_data.qr_type == QRCodeType.AUTH:
            return {
                "auth_token": qr_data.data.get("token"),
                "expires_at": qr_data.data.get("expires_at"),
                "user_id": qr_data.data.get("user_id"),
            }
        else:
            return qr_data.data
    
    async def generate_payment_qr(
        self,
        order_id: int,
        order_number: str,
        amount: float,
        merchant_id: str,
        merchant_name: str,
    ) -> bytes:
        """Generate payment QR code."""
        payment_data = QRPaymentData(
            order_id=order_id,
            order_number=order_number,
            amount=amount,
            merchant_id=merchant_id,
            merchant_name=merchant_name,
        )
        return await self.generate_qr_code(
            QRCodeType.PAYMENT,
            payment_data.to_dict(),
        )
    
    async def generate_product_qr(
        self,
        product_id: int,
        product_name: str,
        price: float,
        vendor_id: int,
        vendor_name: str,
    ) -> bytes:
        """Generate product QR code."""
        product_data = QRProductData(
            product_id=product_id,
            product_name=product_name,
            price=price,
            vendor_id=vendor_id,
            vendor_name=vendor_name,
        )
        return await self.generate_qr_code(
            QRCodeType.PRODUCT,
            product_data.to_dict(),
        )
    
    async def generate_auth_qr(
        self,
        user_id: int,
        token: str,
        expires_in_seconds: int = 300,
    ) -> bytes:
        """Generate authentication QR code."""
        auth_data = {
            "user_id": user_id,
            "token": token,
            "expires_at": (datetime.utcnow() + timedelta(seconds=expires_in_seconds)).isoformat(),
        }
        return await self.generate_qr_code(QRCodeType.AUTH, auth_data)


# Global QR scanner integration
qr_scanner = QRScannerIntegration()


async def generate_qr_code(
    qr_type: str,
    data: Dict[str, Any],
    size: int = 300,
) -> bytes:
    """Generate QR code."""
    return await qr_scanner.generate_qr_code(QRCodeType(qr_type), data, size)


async def scan_qr_code(image_data: bytes) -> Optional[Dict[str, Any]]:
    """Scan QR code from image."""
    result = await qr_scanner.scan_qr_code(image_data)
    if result:
        return await qr_scanner.decode_qr_data(result)
    return None


async def decode_qr_data(qr_data_str: str) -> Dict[str, Any]:
    """Decode QR code data string."""
    qr_data = QRCodeData.from_json(qr_data_str)
    return await qr_scanner.decode_qr_data(qr_data)


__all__ = [
    "QRScannerIntegration",
    "QRCodeData",
    "QRCodeType",
    "QRPaymentData",
    "QRProductData",
    "qr_scanner",
    "generate_qr_code",
    "scan_qr_code",
    "decode_qr_data",
]