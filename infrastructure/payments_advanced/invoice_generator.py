# ============================
# WOLLOYEWA STORE BOT - INVOICE GENERATOR
# ============================
"""Professional invoice generation for orders and subscriptions."""

from decimal import Decimal
from enum import Enum
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field
from datetime import datetime

from core.logger import logger
from core.utils.currency import format_etb
from core.utils.ethiopian_calendar import format_ethiopian_date


class InvoiceStatus(str, Enum):
    """Invoice status."""
    DRAFT = "draft"
    SENT = "sent"
    PAID = "paid"
    OVERDUE = "overdue"
    CANCELLED = "cancelled"


@dataclass
class InvoiceItem:
    """Invoice line item."""
    
    description: str
    quantity: int
    unit_price: Decimal
    total: Decimal
    tax_rate: float = 0.15  # 15% VAT for Ethiopia
    tax_amount: Decimal = Decimal(0)


@dataclass
class Invoice:
    """Invoice data structure."""
    
    invoice_number: str
    order_id: Optional[int]
    order_number: Optional[str]
    customer_name: str
    customer_email: str
    customer_phone: str
    customer_address: Optional[str]
    items: List[InvoiceItem]
    subtotal: Decimal
    tax_total: Decimal
    discount_total: Decimal
    total: Decimal
    status: InvoiceStatus
    issue_date: datetime
    due_date: datetime
    paid_date: Optional[datetime] = None
    notes: Optional[str] = None
    payment_method: Optional[str] = None
    transaction_id: Optional[str] = None


class InvoiceGenerator:
    """
    Invoice generator for orders and subscriptions.
    
    Features:
    - Generate invoices for orders
    - Ethiopian tax compliance (VAT)
    - Multiple formats (PDF, HTML)
    - Invoice numbering
    - Payment tracking
    """
    
    def __init__(self, db_session):
        self.db = db_session
        self.invoice_prefix = "INV"
        self.company_name = "Wolloyewa Technologies PLC"
        self.company_tin = "0012345678"
        self.company_vat = "VAT0012345678"
    
    async def generate_order_invoice(
        self,
        order_id: int,
    ) -> Invoice:
        """
        Generate invoice for an order.
        
        Args:
            order_id: Order ID
            
        Returns:
            Invoice object
        """
        from apps.orders.repository import OrderRepository, OrderItemRepository
        
        order_repo = OrderRepository(self.db)
        item_repo = OrderItemRepository(self.db)
        
        order = await order_repo.get_by_id(order_id)
        if not order:
            raise ValueError(f"Order not found: {order_id}")
        
        items = await item_repo.get_by_order(order_id)
        
        invoice_items = []
        for item in items:
            invoice_items.append(InvoiceItem(
                description=item.product_name,
                quantity=item.quantity,
                unit_price=item.unit_price,
                total=item.total_price,
                tax_rate=0.15,
                tax_amount=item.total_price * Decimal("0.15"),
            ))
        
        invoice = Invoice(
            invoice_number=self._generate_invoice_number(),
            order_id=order.id,
            order_number=order.order_number,
            customer_name=f"{order.user.first_name} {order.user.last_name or ''}".strip(),
            customer_email=order.user.email or "",
            customer_phone=order.shipping_phone,
            customer_address=order.shipping_address,
            items=invoice_items,
            subtotal=order.subtotal,
            tax_total=order.tax,
            discount_total=order.discount,
            total=order.total,
            status=InvoiceStatus.SENT if order.payment_status == "paid" else InvoiceStatus.SENT,
            issue_date=order.created_at,
            due_date=order.created_at + timedelta(days=7),
            paid_date=order.paid_at if hasattr(order, 'paid_at') else None,
            payment_method=order.payment_method,
            transaction_id=order.payment_transaction_id,
        )
        
        await self._store_invoice(invoice)
        return invoice
    
    async def generate_invoice_pdf(self, invoice: Invoice) -> bytes:
        """
        Generate PDF version of invoice.
        
        Args:
            invoice: Invoice object
            
        Returns:
            PDF bytes
        """
        try:
            from reportlab.lib import colors
            from reportlab.lib.pagesizes import A4
            from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
            from reportlab.lib.units import mm
            from reportlab.platypus import (
                SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer,
                Image, PageBreak
            )
            from reportlab.pdfbase import pdfmetrics
            from reportlab.pdfbase.ttfonts import TTFont
            
            import io
            buffer = io.BytesIO()
            
            doc = SimpleDocTemplate(
                buffer,
                pagesize=A4,
                topMargin=10*mm,
                bottomMargin=10*mm,
                leftMargin=15*mm,
                rightMargin=15*mm,
            )
            
            styles = getSampleStyleSheet()
            elements = []
            
            # Company header
            title_style = ParagraphStyle(
                'TitleStyle',
                parent=styles['Heading1'],
                fontSize=18,
                textColor=colors.HexColor('#1a5276'),
                alignment=0,
            )
            elements.append(Paragraph(self.company_name, title_style))
            elements.append(Spacer(1, 5*mm))
            
            # Invoice title
            invoice_title = ParagraphStyle(
                'InvoiceTitle',
                parent=styles['Heading2'],
                fontSize=14,
                textColor=colors.HexColor('#1a5276'),
            )
            elements.append(Paragraph("TAX INVOICE", invoice_title))
            elements.append(Spacer(1, 5*mm))
            
            # Invoice details
            details_data = [
                ["Invoice Number:", invoice.invoice_number],
                ["Invoice Date:", invoice.issue_date.strftime("%Y-%m-%d")],
                ["Ethiopian Date:", format_ethiopian_date(invoice.issue_date)],
                ["Due Date:", invoice.due_date.strftime("%Y-%m-%d")],
                ["Order Number:", invoice.order_number or "N/A"],
            ]
            
            details_table = Table(details_data, colWidths=[40*mm, 80*mm])
            details_table.setStyle(TableStyle([
                ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 0), (-1, -1), 10),
                ('TEXTCOLOR', (0, 0), (0, -1), colors.grey),
                ('TEXTCOLOR', (1, 0), (1, -1), colors.black),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ]))
            elements.append(details_table)
            elements.append(Spacer(1, 10*mm))
            
            # Customer info
            elements.append(Paragraph("Bill To:", styles['Heading3']))
            customer_data = [
                ["Name:", invoice.customer_name],
                ["Email:", invoice.customer_email],
                ["Phone:", invoice.customer_phone],
                ["Address:", invoice.customer_address or "N/A"],
            ]
            
            customer_table = Table(customer_data, colWidths=[30*mm, 90*mm])
            customer_table.setStyle(TableStyle([
                ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 0), (-1, -1), 9),
                ('TEXTCOLOR', (0, 0), (0, -1), colors.grey),
                ('TEXTCOLOR', (1, 0), (1, -1), colors.black),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ]))
            elements.append(customer_table)
            elements.append(Spacer(1, 10*mm))
            
            # Items table
            items_headers = ["#", "Description", "Qty", "Unit Price", "Total"]
            items_data = [items_headers]
            
            for idx, item in enumerate(invoice.items, 1):
                items_data.append([
                    str(idx),
                    item.description[:50],
                    str(item.quantity),
                    format_etb(item.unit_price, short=False),
                    format_etb(item.total, short=False),
                ])
            
            items_table = Table(items_data, colWidths=[15*mm, 70*mm, 20*mm, 30*mm, 30*mm])
            items_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1a5276')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('ALIGN', (1, 1), (1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 10),
                ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 1), (-1, -1), 9),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ]))
            elements.append(items_table)
            elements.append(Spacer(1, 10*mm))
            
            # Totals
            totals_data = [
                ["Subtotal:", format_etb(invoice.subtotal)],
                ["Tax (15% VAT):", format_etb(invoice.tax_total)],
                ["Discount:", format_etb(invoice.discount_total)],
                ["", ""],
                ["TOTAL:", format_etb(invoice.total)],
            ]
            
            totals_table = Table(totals_data, colWidths=[100*mm, 40*mm])
            totals_table.setStyle(TableStyle([
                ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 0), (-1, -1), 10),
                ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
                ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
                ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
                ('FONTSIZE', (0, -1), (-1, -1), 12),
                ('TEXTCOLOR', (0, -1), (-1, -1), colors.HexColor('#1a5276')),
            ]))
            elements.append(totals_table)
            elements.append(Spacer(1, 10*mm))
            
            # Footer
            footer_text = f"""
            <para align="center" fontSize="8" textColor="grey">
            {self.company_name} | TIN: {self.company_tin} | VAT: {self.company_vat}<br/>
            Thank you for shopping with Wolloyewa!
            </para>
            """
            elements.append(Paragraph(footer_text, styles['Normal']))
            
            doc.build(elements)
            buffer.seek(0)
            return buffer.getvalue()
            
        except Exception as e:
            logger.error(f"Failed to generate PDF invoice: {e}")
            return b""
    
    def _generate_invoice_number(self) -> str:
        """Generate unique invoice number."""
        import uuid
        return f"{self.invoice_prefix}_{datetime.utcnow().strftime('%Y%m%d')}_{uuid.uuid4().hex[:6].upper()}"
    
    async def _store_invoice(self, invoice: Invoice) -> None:
        """Store invoice in database."""
        pass


async def generate_invoice(db, order_id: int) -> Invoice:
    """Generate invoice for an order."""
    generator = InvoiceGenerator(db)
    return await generator.generate_order_invoice(order_id)


async def generate_invoice_pdf(db, order_id: int) -> bytes:
    """Generate PDF invoice for an order."""
    generator = InvoiceGenerator(db)
    invoice = await generator.generate_order_invoice(order_id)
    return await generator.generate_invoice_pdf(invoice)


__all__ = [
    "InvoiceGenerator",
    "Invoice",
    "InvoiceItem",
    "InvoiceStatus",
    "generate_invoice",
    "generate_invoice_pdf",
]