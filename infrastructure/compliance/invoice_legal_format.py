# ============================
# WOLLOYEWA STORE BOT - LEGAL INVOICE FORMAT
# ============================
"""Ethiopian legal invoice format compliance."""

from enum import Enum
from decimal import Decimal
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field
from datetime import datetime

from core.logger import logger
from infrastructure.compliance.tax_calculator import TaxCalculator, TaxCategory, TaxResult


class InvoiceType(str, Enum):
    """Types of legal invoices."""
    TAX_INVOICE = "tax_invoice"
    RECEIPT = "receipt"
    PROFORMA = "proforma"
    CREDIT_NOTE = "credit_note"
    DEBIT_NOTE = "debit_note"


@dataclass
class LegalInvoice:
    """Legal invoice data structure."""
    
    invoice_number: str
    invoice_type: InvoiceType
    issue_date: datetime
    due_date: Optional[datetime]
    
    # Seller info
    seller_name: str
    seller_tin: str
    seller_vat_number: str
    seller_address: str
    
    # Buyer info
    buyer_name: str
    buyer_tin: Optional[str]
    buyer_vat_number: Optional[str]
    buyer_address: str
    
    # Invoice details
    order_number: str
    currency: str = "ETB"
    
    # Tax results
    tax_result: Optional[TaxResult] = None
    
    # Items
    items: List[Dict[str, Any]] = field(default_factory=list)
    
    # Totals
    subtotal: Decimal = Decimal("0")
    shipping_fee: Decimal = Decimal("0")
    discount: Decimal = Decimal("0")
    vat_amount: Decimal = Decimal("0")
    withholding_tax: Decimal = Decimal("0")
    total_amount: Decimal = Decimal("0")
    
    # Additional info
    notes: Optional[str] = None
    qr_code_data: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "invoice_number": self.invoice_number,
            "invoice_type": self.invoice_type.value,
            "issue_date": self.issue_date.isoformat(),
            "due_date": self.due_date.isoformat() if self.due_date else None,
            "seller": {
                "name": self.seller_name,
                "tin": self.seller_tin,
                "vat_number": self.seller_vat_number,
                "address": self.seller_address,
            },
            "buyer": {
                "name": self.buyer_name,
                "tin": self.buyer_tin,
                "vat_number": self.buyer_vat_number,
                "address": self.buyer_address,
            },
            "order_number": self.order_number,
            "currency": self.currency,
            "items": self.items,
            "subtotal": float(self.subtotal),
            "shipping_fee": float(self.shipping_fee),
            "discount": float(self.discount),
            "vat_amount": float(self.vat_amount),
            "withholding_tax": float(self.withholding_tax),
            "total_amount": float(self.total_amount),
            "notes": self.notes,
        }


class LegalInvoiceGenerator:
    """
    Legal invoice generator for Ethiopian tax compliance.
    
    Features:
    - Ethiopian tax invoice format
    - TIN and VAT number validation
    - Sequential invoice numbering
    - QR code generation for verification
    """
    
    def __init__(self):
        self.tax_calculator = TaxCalculator()
        self._invoice_counter = 1
        self._invoice_prefix = "INV"
    
    def set_invoice_counter(self, counter: int) -> None:
        """Set the invoice counter for sequential numbering."""
        self._invoice_counter = counter
    
    def generate_invoice_number(self) -> str:
        """Generate sequential invoice number."""
        invoice_num = f"{self._invoice_prefix}{datetime.utcnow().strftime('%Y%m')}{self._invoice_counter:06d}"
        self._invoice_counter += 1
        return invoice_num
    
    async def generate_legal_invoice(
        self,
        order: Dict[str, Any],
        items: List[Dict[str, Any]],
        seller_info: Dict[str, str],
        buyer_info: Dict[str, str],
        invoice_type: InvoiceType = InvoiceType.TAX_INVOICE,
    ) -> LegalInvoice:
        """
        Generate a legal invoice for an order.
        
        Args:
            order: Order data
            items: Order items
            seller_info: Seller information
            buyer_info: Buyer information
            invoice_type: Type of invoice
            
        Returns:
            LegalInvoice object
        """
        # Calculate subtotal
        subtotal = sum(item.get("total_price", 0) for item in items)
        
        # Calculate taxes
        tax_result = self.tax_calculator.calculate_invoice_tax(
            subtotal=Decimal(str(subtotal)),
            shipping_fee=Decimal(str(order.get("shipping_fee", 0))),
            discount=Decimal(str(order.get("discount", 0))),
            tax_category=TaxCategory.STANDARD,
            is_vat_registered=True,
            is_company=True,
            has_tin=bool(seller_info.get("tin")),
        )
        
        # Prepare invoice items
        invoice_items = []
        for item in items:
            invoice_items.append({
                "description": item.get("product_name", ""),
                "quantity": item.get("quantity", 1),
                "unit_price": float(item.get("unit_price", 0)),
                "total": float(item.get("total_price", 0)),
                "tax_category": TaxCategory.STANDARD.value,
            })
        
        invoice = LegalInvoice(
            invoice_number=self.generate_invoice_number(),
            invoice_type=invoice_type,
            issue_date=datetime.utcnow(),
            due_date=datetime.utcnow(),  # Adjust as needed
            seller_name=seller_info.get("name", ""),
            seller_tin=seller_info.get("tin", ""),
            seller_vat_number=seller_info.get("vat_number", ""),
            seller_address=seller_info.get("address", ""),
            buyer_name=buyer_info.get("name", ""),
            buyer_tin=buyer_info.get("tin"),
            buyer_vat_number=buyer_info.get("vat_number"),
            buyer_address=buyer_info.get("address", ""),
            order_number=order.get("order_number", ""),
            tax_result=tax_result,
            items=invoice_items,
            subtotal=Decimal(str(subtotal)),
            shipping_fee=Decimal(str(order.get("shipping_fee", 0))),
            discount=Decimal(str(order.get("discount", 0))),
            vat_amount=tax_result.vat_amount,
            withholding_tax=tax_result.withholding_tax,
            total_amount=tax_result.net_amount,
            notes=order.get("notes"),
        )
        
        # Generate QR code for verification
        invoice.qr_code_data = self._generate_qr_code_data(invoice)
        
        logger.info(f"Generated legal invoice: {invoice.invoice_number}")
        return invoice
    
    def _generate_qr_code_data(self, invoice: LegalInvoice) -> str:
        """Generate QR code data for invoice verification."""
        # Format: INVOICE|NUMBER|TIN|DATE|AMOUNT
        return f"INVOICE|{invoice.invoice_number}|{invoice.seller_tin}|{invoice.issue_date.strftime('%Y%m%d')}|{invoice.total_amount}"
    
    async def validate_invoice_for_tax(self, invoice: LegalInvoice) -> Dict[str, Any]:
        """
        Validate invoice for tax compliance.
        
        Args:
            invoice: LegalInvoice to validate
            
        Returns:
            Validation result
        """
        errors = []
        warnings = []
        
        # Check required fields
        required_fields = ["invoice_number", "seller_tin", "buyer_name", "order_number"]
        for field in required_fields:
            if not getattr(invoice, field, None):
                errors.append(f"Missing required field: {field}")
        
        # Validate TIN format
        if invoice.seller_tin and not self._validate_tin(invoice.seller_tin):
            errors.append("Invalid seller TIN format")
        
        if invoice.buyer_tin and not self._validate_tin(invoice.buyer_tin):
            warnings.append("Invalid buyer TIN format")
        
        # Validate tax calculation
        if invoice.tax_result:
            expected_total = (
                invoice.subtotal +
                invoice.shipping_fee -
                invoice.discount
            )
            
            if abs(float(expected_total) - float(invoice.total_amount)) > 0.01:
                errors.append(f"Tax calculation mismatch: expected {expected_total}, got {invoice.total_amount}")
        
        return {
            "is_valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings,
            "invoice_number": invoice.invoice_number,
        }
    
    def _validate_tin(self, tin: str) -> bool:
        """Validate Ethiopian TIN format (10 digits)."""
        import re
        return bool(re.match(r'^\d{10}$', tin))


# Global legal invoice generator
legal_invoice_generator = LegalInvoiceGenerator()


async def generate_legal_invoice(
    order: Dict[str, Any],
    items: List[Dict[str, Any]],
    seller_info: Dict[str, str],
    buyer_info: Dict[str, str],
) -> LegalInvoice:
    """Generate a legal invoice."""
    return await legal_invoice_generator.generate_legal_invoice(
        order, items, seller_info, buyer_info
    )


async def validate_invoice_for_tax(invoice: LegalInvoice) -> Dict[str, Any]:
    """Validate invoice for tax compliance."""
    return await legal_invoice_generator.validate_invoice_for_tax(invoice)


TaxInvoice = LegalInvoice
ReceiptInvoice = LegalInvoice

__all__ = [
    "LegalInvoiceGenerator",
    "LegalInvoice",
    "InvoiceType",
    "legal_invoice_generator",
    "generate_legal_invoice",
    "validate_invoice_for_tax",
    "TaxInvoice",
    "ReceiptInvoice",
]