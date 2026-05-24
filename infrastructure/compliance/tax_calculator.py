# ============================
# WOLLOYEWA STORE BOT - TAX CALCULATOR
# ============================
"""Ethiopian tax calculation for VAT, withholding tax, and turnover tax."""

from enum import Enum
from decimal import Decimal
from typing import Optional, Dict, Any
from dataclasses import dataclass, field

from core.logger import logger


class TaxCategory(str, Enum):
    """Tax categories for products."""
    STANDARD = "standard"      # 15% VAT
    ZERO_RATED = "zero_rated"  # 0% VAT (exports)
    EXEMPT = "exempt"          # No VAT (basic food items, etc.)
    SERVICES = "services"      # Services (15% VAT + withholding)


class TaxRate:
    """Ethiopian tax rates."""
    
    VAT_STANDARD = Decimal("0.15")      # 15% Value Added Tax
    VAT_ZERO = Decimal("0.00")          # 0% for exports
    WITHHOLDING = Decimal("0.02")       # 2% withholding tax for payments to suppliers
    TURNOVER_THRESHOLD = Decimal("1000000")  # 1,000,000 ETB threshold
    TURNOVER_TAX_RATE = Decimal("0.02")      # 2% turnover tax for businesses below threshold


@dataclass
class TaxResult:
    """Result of tax calculation."""
    
    taxable_amount: Decimal
    vat_amount: Decimal
    withholding_tax: Decimal
    turnover_tax: Decimal
    total_tax: Decimal
    net_amount: Decimal
    tax_category: TaxCategory
    breakdown: Dict[str, Decimal] = field(default_factory=dict)


class TaxCalculator:
    """
    Ethiopian tax calculator.
    
    Features:
    - VAT calculation (15%)
    - Withholding tax (2%)
    - Turnover tax for small businesses
    - Tax category management
    """
    
    def __init__(self):
        self.vat_rate = TaxRate.VAT_STANDARD
        self.withholding_rate = TaxRate.WITHHOLDING
        self.turnover_tax_rate = TaxRate.TURNOVER_TAX_RATE
        self.turnover_threshold = TaxRate.TURNOVER_THRESHOLD
    
    def calculate_vat(
        self,
        amount: Decimal,
        category: TaxCategory = TaxCategory.STANDARD,
        is_vat_registered: bool = True,
    ) -> Decimal:
        """
        Calculate VAT for an amount.
        
        Args:
            amount: Amount to calculate VAT on
            category: Tax category of the product
            is_vat_registered: Whether seller is VAT registered
            
        Returns:
            VAT amount
        """
        if not is_vat_registered:
            return Decimal("0.00")
        
        if category == TaxCategory.STANDARD:
            return (amount * self.vat_rate).quantize(Decimal("0.01"))
        elif category == TaxCategory.ZERO_RATED:
            return Decimal("0.00")
        elif category == TaxCategory.EXEMPT:
            return Decimal("0.00")
        else:
            return (amount * self.vat_rate).quantize(Decimal("0.01"))
    
    def calculate_withholding_tax(
        self,
        amount: Decimal,
        is_company: bool = True,
        has_tin: bool = True,
    ) -> Decimal:
        """
        Calculate withholding tax.
        
        Args:
            amount: Payment amount
            is_company: Whether recipient is a company
            has_tin: Whether recipient has TIN
            
        Returns:
            Withholding tax amount
        """
        # Withholding tax applies to payments to companies with TIN
        if not is_company or not has_tin:
            return Decimal("0.00")
        
        return (amount * self.withholding_rate).quantize(Decimal("0.01"))
    
    def calculate_turnover_tax(
        self,
        amount: Decimal,
        annual_revenue: Decimal,
    ) -> Decimal:
        """
        Calculate turnover tax for businesses below VAT threshold.
        
        Args:
            amount: Transaction amount
            annual_revenue: Seller's annual revenue
            
        Returns:
            Turnover tax amount
        """
        if annual_revenue >= self.turnover_threshold:
            # VAT registered, no turnover tax
            return Decimal("0.00")
        
        return (amount * self.turnover_tax_rate).quantize(Decimal("0.01"))
    
    def calculate_total_tax(
        self,
        amount: Decimal,
        tax_category: TaxCategory = TaxCategory.STANDARD,
        is_vat_registered: bool = True,
        is_company: bool = True,
        has_tin: bool = True,
        annual_revenue: Optional[Decimal] = None,
    ) -> TaxResult:
        """
        Calculate all applicable taxes.
        
        Args:
            amount: Transaction amount
            tax_category: Product tax category
            is_vat_registered: Whether seller is VAT registered
            is_company: Whether seller is a company
            has_tin: Whether seller has TIN
            annual_revenue: Seller's annual revenue
            
        Returns:
            TaxResult with all tax components
        """
        annual_revenue = annual_revenue or self.turnover_threshold + Decimal("1")
        
        # Calculate each tax
        vat = self.calculate_vat(amount, tax_category, is_vat_registered)
        withholding = self.calculate_withholding_tax(amount, is_company, has_tin)
        turnover = self.calculate_turnover_tax(amount, annual_revenue)
        
        total_tax = vat + withholding + turnover
        net_amount = amount - total_tax
        
        breakdown = {
            "vat": vat,
            "withholding_tax": withholding,
            "turnover_tax": turnover,
        }
        
        return TaxResult(
            taxable_amount=amount,
            vat_amount=vat,
            withholding_tax=withholding,
            turnover_tax=turnover,
            total_tax=total_tax,
            net_amount=net_amount,
            tax_category=tax_category,
            breakdown=breakdown,
        )
    
    def calculate_invoice_tax(
        self,
        subtotal: Decimal,
        shipping_fee: Decimal = Decimal("0"),
        discount: Decimal = Decimal("0"),
        **kwargs,
    ) -> TaxResult:
        """
        Calculate tax for an invoice.
        
        Args:
            subtotal: Invoice subtotal
            shipping_fee: Shipping fee
            discount: Discount amount
            
        Returns:
            TaxResult for the invoice
        """
        taxable_amount = subtotal + shipping_fee - discount
        
        return self.calculate_total_tax(taxable_amount, **kwargs)
    
    def get_tax_summary(self, transactions: list) -> Dict[str, Decimal]:
        """
        Get tax summary for multiple transactions.
        
        Args:
            transactions: List of transaction amounts or TaxResults
            
        Returns:
            Summary of total taxes
        """
        total_vat = Decimal("0")
        total_withholding = Decimal("0")
        total_turnover = Decimal("0")
        total_taxable = Decimal("0")
        
        for tx in transactions:
            if isinstance(tx, TaxResult):
                total_vat += tx.vat_amount
                total_withholding += tx.withholding_tax
                total_turnover += tx.turnover_tax
                total_taxable += tx.taxable_amount
            else:
                # Simple amount, assume standard tax
                result = self.calculate_total_tax(tx)
                total_vat += result.vat_amount
                total_withholding += result.withholding_tax
                total_turnover += result.turnover_tax
                total_taxable += tx
        
        return {
            "total_taxable": total_taxable,
            "total_vat": total_vat,
            "total_withholding_tax": total_withholding,
            "total_turnover_tax": total_turnover,
            "total_tax": total_vat + total_withholding + total_turnover,
        }


# Global tax calculator instance
tax_calculator = TaxCalculator()


def calculate_vat(amount: Decimal, category: TaxCategory = TaxCategory.STANDARD) -> Decimal:
    """Calculate VAT for an amount."""
    return tax_calculator.calculate_vat(amount, category)


def calculate_withholding_tax(amount: Decimal, is_company: bool = True, has_tin: bool = True) -> Decimal:
    """Calculate withholding tax."""
    return tax_calculator.calculate_withholding_tax(amount, is_company, has_tin)


def calculate_turnover_tax(amount: Decimal, annual_revenue: Decimal) -> Decimal:
    """Calculate turnover tax."""
    return tax_calculator.calculate_turnover_tax(amount, annual_revenue)


def calculate_total_tax(amount: Decimal, **kwargs) -> TaxResult:
    """Calculate all applicable taxes."""
    return tax_calculator.calculate_total_tax(amount, **kwargs)


__all__ = [
    "TaxCalculator",
    "TaxCategory",
    "TaxRate",
    "TaxResult",
    "tax_calculator",
    "calculate_vat",
    "calculate_withholding_tax",
    "calculate_turnover_tax",
    "calculate_total_tax",
]