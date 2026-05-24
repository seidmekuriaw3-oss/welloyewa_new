# ============================
# WOLLOYEWA STORE BOT - INVOICE GENERATOR
# ============================
"""PDF invoice generation for orders with Ethiopian tax requirements."""

import io
from datetime import datetime
from decimal import Decimal
from typing import Optional, Dict, Any, List
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import qrcode
from PIL import Image as PILImage

from core.logger import logger
from core.config import settings
from core.utils.currency import format_etb
from core.utils.ethiopian_calendar import format_ethiopian_date


class InvoiceGenerator:
    """
    Generate PDF invoices for orders.
    
    Features:
    - Ethiopian tax invoice format
    - QR code for verification
    - Amharic text support
    - Digital signature ready
    """
    
    def __init__(self):
        self.company_name = "Wolloyewa Technologies PLC"
        self.company_address = "Addis Ababa, Ethiopia"
        self.company_phone = "+251-XXX-XXX-XXX"
        self.company_email = "info@wolloyewa.com"
        self.tin_number = "0012345678"
        self.vat_number = "VAT0012345678"
    
    async def generate_invoice(
        self,
        order: Dict[str, Any],
        items: List[Dict[str, Any]],
    ) -> bytes:
        """
        Generate PDF invoice for an order.
        
        Args:
            order: Order data dictionary
            items: List of order items
            
        Returns:
            PDF bytes
        """
        buffer = io.BytesIO()
        
        # Create PDF document
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            topMargin=10*mm,
            bottomMargin=10*mm,
            leftMargin=15*mm,
            rightMargin=15*mm,
        )
        
        # Build document elements
        elements = []
        
        # Add header
        elements.extend(self._build_header(order))
        
        # Add customer info
        elements.extend(self._build_customer_info(order))
        
        # Add items table
        elements.extend(self._build_items_table(items, order))
        
        # Add totals
        elements.extend(self._build_totals(order))
        
        # Add payment info
        elements.extend(self._build_payment_info(order))
        
        # Add QR code for verification
        qr_image = self._generate_qr_code(order)
        if qr_image:
            elements.append(Spacer(1, 10*mm))
            elements.append(qr_image)
        
        # Add footer
        elements.extend(self._build_footer())
        
        # Build PDF
        doc.build(elements)
        
        buffer.seek(0)
        return buffer.getvalue()
    
    def _build_header(self, order: Dict[str, Any]) -> list:
        """Build invoice header section."""
        styles = getSampleStyleSheet()
        
        # Custom styles
        title_style = ParagraphStyle(
            'TitleStyle',
            parent=styles['Heading1'],
            fontSize=20,
            textColor=colors.HexColor('#1a5276'),
            alignment=1,  # Center
            spaceAfter=6,
        )
        
        subtitle_style = ParagraphStyle(
            'SubtitleStyle',
            parent=styles['Normal'],
            fontSize=10,
            textColor=colors.grey,
            alignment=1,
        )
        
        elements = []
        
        # Company name
        elements.append(Paragraph(self.company_name, title_style))
        elements.append(Paragraph("Tax Invoice", styles['Heading2']))
        
        # Invoice details
        invoice_info = [
            ["Invoice Number:", f"INV-{order.get('order_number', 'N/A')}"],
            ["Invoice Date:", datetime.utcnow().strftime("%Y-%m-%d %H:%M")],
            ["Ethiopian Date:", format_ethiopian_date(datetime.utcnow())],
            ["Order Number:", order.get('order_number', 'N/A')],
            ["Order Date:", order.get('created_at', '').split('T')[0] if order.get('created_at') else 'N/A'],
        ]
        
        info_table = Table(invoice_info, colWidths=[60*mm, 80*mm])
        info_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('TEXTCOLOR', (0, 0), (0, -1), colors.grey),
            ('TEXTCOLOR', (1, 0), (1, -1), colors.black),
            ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
            ('ALIGN', (1, 0), (1, -1), 'LEFT'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))
        
        elements.append(Spacer(1, 5*mm))
        elements.append(info_table)
        elements.append(Spacer(1, 5*mm))
        
        return elements
    
    def _build_customer_info(self, order: Dict[str, Any]) -> list:
        """Build customer information section."""
        styles = getSampleStyleSheet()
        
        elements = []
        
        # Section title
        elements.append(Paragraph("Customer Information", styles['Heading3']))
        
        # Customer details
        customer_info = [
            ["Name:", order.get('customer_name', 'N/A')],
            ["Phone:", order.get('shipping_phone', 'N/A')],
            ["Email:", order.get('customer_email', 'N/A')],
            ["Shipping Address:", order.get('shipping_address', 'N/A')],
            ["City:", order.get('shipping_city', 'N/A')],
        ]
        
        info_table = Table(customer_info, colWidths=[40*mm, 100*mm])
        info_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('TEXTCOLOR', (0, 0), (0, -1), colors.grey),
            ('TEXTCOLOR', (1, 0), (1, -1), colors.black),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ]))
        
        elements.append(info_table)
        elements.append(Spacer(1, 5*mm))
        
        return elements
    
    def _build_items_table(self, items: List[Dict[str, Any]], order: Dict[str, Any]) -> list:
        """Build order items table."""
        styles = getSampleStyleSheet()
        
        elements = []
        elements.append(Paragraph("Order Items", styles['Heading3']))
        
        # Table headers
        headers = ["#", "Product", "SKU", "Qty", "Unit Price", "Total"]
        
        # Table data
        data = [headers]
        
        for idx, item in enumerate(items, 1):
            data.append([
                str(idx),
                item.get('product_name', 'N/A')[:40],
                item.get('product_sku', 'N/A'),
                str(item.get('quantity', 0)),
                format_etb(item.get('unit_price', 0)),
                format_etb(item.get('total_price', 0)),
            ])
        
        # Create table
        table = Table(data, colWidths=[15*mm, 65*mm, 30*mm, 20*mm, 30*mm, 30*mm])
        
        # Table styling
        table.setStyle(TableStyle([
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
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ]))
        
        elements.append(table)
        elements.append(Spacer(1, 5*mm))
        
        return elements
    
    def _build_totals(self, order: Dict[str, Any]) -> list:
        """Build totals section."""
        elements = []
        
        totals_data = [
            ["Subtotal:", format_etb(order.get('subtotal', 0))],
            ["Shipping Fee:", format_etb(order.get('shipping_fee', 0))],
            ["Tax (15% VAT):", format_etb(order.get('tax', 0))],
            ["Discount:", format_etb(order.get('discount', 0))],
            ["", ""],
            ["TOTAL:", format_etb(order.get('total', 0))],
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
        elements.append(Spacer(1, 5*mm))
        
        return elements
    
    def _build_payment_info(self, order: Dict[str, Any]) -> list:
        """Build payment information section."""
        styles = getSampleStyleSheet()
        
        elements = []
        elements.append(Paragraph("Payment Information", styles['Heading3']))
        
        payment_info = [
            ["Payment Method:", order.get('payment_method', 'N/A')],
            ["Payment Status:", order.get('payment_status', 'N/A')],
            ["Transaction ID:", order.get('payment_transaction_id', 'N/A') or 'N/A'],
        ]
        
        info_table = Table(payment_info, colWidths=[40*mm, 100*mm])
        info_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('TEXTCOLOR', (0, 0), (0, -1), colors.grey),
            ('TEXTCOLOR', (1, 0), (1, -1), colors.black),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))
        
        elements.append(info_table)
        elements.append(Spacer(1, 5*mm))
        
        return elements
    
    def _generate_qr_code(self, order: Dict[str, Any]) -> Optional[Image]:
        """Generate QR code for invoice verification."""
        try:
            # Create verification URL
            verification_url = f"https://verify.wolloyewa.com/invoice/{order.get('order_number')}"
            
            # Generate QR code
            qr = qrcode.QRCode(version=1, box_size=4, border=2)
            qr.add_data(verification_url)
            qr.make(fit=True)
            
            # Create QR code image
            qr_img = qr.make_image(fill_color="black", back_color="white")
            
            # Convert to bytes
            img_buffer = io.BytesIO()
            qr_img.save(img_buffer, format='PNG')
            img_buffer.seek(0)
            
            # Add to PDF
            pil_img = PILImage.open(img_buffer)
            img = Image(pil_img, width=40*mm, height=40*mm)
            
            return img
        except Exception as e:
            logger.error(f"Failed to generate QR code: {e}")
            return None
    
    def _build_footer(self) -> list:
        """Build invoice footer."""
        styles = getSampleStyleSheet()
        
        elements = []
        
        footer_text = f"""
        <para align="center" fontSize="8" textColor="grey">
        {self.company_name} | TIN: {self.tin_number} | VAT: {self.vat_number}<br/>
        {self.company_address} | Tel: {self.company_phone} | Email: {self.company_email}<br/>
        Thank you for shopping with Wolloyewa!
        </para>
        """
        
        elements.append(Paragraph(footer_text, styles['Normal']))
        elements.append(Spacer(1, 10*mm))
        
        return elements


async def generate_order_invoice(order_id: int, db) -> bytes:
    """
    Convenience function to generate invoice for an order.
    
    Args:
        order_id: Order ID
        db: Database session
        
    Returns:
        PDF bytes
    """
    from apps.orders.repository import OrderRepository, OrderItemRepository
    
    order_repo = OrderRepository(db)
    item_repo = OrderItemRepository(db)
    
    order = await order_repo.get_by_id(order_id)
    if not order:
        raise ValueError(f"Order {order_id} not found")
    
    items = await item_repo.get_by_order(order_id)
    
    order_dict = {
        "order_number": order.order_number,
        "created_at": order.created_at.isoformat(),
        "customer_name": f"{order.user.first_name} {order.user.last_name or ''}",
        "customer_email": order.user.email,
        "shipping_phone": order.shipping_phone,
        "shipping_address": order.shipping_address,
        "shipping_city": order.shipping_city,
        "subtotal": float(order.subtotal),
        "shipping_fee": float(order.shipping_fee),
        "tax": float(order.tax),
        "discount": float(order.discount),
        "total": float(order.total),
        "payment_method": order.payment_method,
        "payment_status": order.payment_status,
        "payment_transaction_id": order.payment_transaction_id,
    }
    
    items_dict = [
        {
            "product_name": item.product_name,
            "product_sku": item.product_sku,
            "quantity": item.quantity,
            "unit_price": float(item.unit_price),
            "total_price": float(item.total_price),
        }
        for item in items
    ]
    
    generator = InvoiceGenerator()
    return await generator.generate_invoice(order_dict, items_dict)


async def generate_invoice_pdf(order_id: int, db) -> bytes:
    """Alias for generate_order_invoice."""
    return await generate_order_invoice(order_id, db)


__all__ = [
    "InvoiceGenerator",
    "generate_order_invoice",
    "generate_invoice_pdf",
]