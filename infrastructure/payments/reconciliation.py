# ============================
# WOLLOYEWA STORE BOT - PAYMENT RECONCILIATION
# ============================
"""Payment reconciliation utilities for matching transactions with orders."""

from datetime import datetime, timedelta
from decimal import Decimal
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

from infrastructure.payments.base import PaymentStatus
from infrastructure.payments.factory import get_payment_provider
from core.logger import logger


class ReconciliationStatus(str, Enum):
    """Status of payment reconciliation."""
    MATCHED = "matched"
    MISMATCHED = "mismatched"
    MISSING = "missing"
    EXTRA = "extra"
    PENDING = "pending"


@dataclass
class ReconciledTransaction:
    """Result of a reconciled transaction."""
    
    gateway_transaction_id: str
    gateway_amount: Decimal
    gateway_status: str
    gateway_date: datetime
    order_id: Optional[int]
    order_amount: Optional[Decimal]
    order_status: Optional[str]
    status: ReconciliationStatus
    discrepancy: Optional[Decimal] = None
    notes: Optional[str] = None


class PaymentReconciliation:
    """
    Payment reconciliation service.
    
    Features:
    - Match gateway transactions with orders
    - Detect missing or extra payments
    - Generate reconciliation reports
    - Automated discrepancy resolution
    """
    
    def __init__(self, db):
        self.db = db
    
    async def get_gateway_transactions(
        self,
        method: str,
        start_date: datetime,
        end_date: datetime,
    ) -> List[Dict[str, Any]]:
        """
        Fetch transactions from payment gateway.
        
        Args:
            method: Payment method
            start_date: Start date
            end_date: End date
            
        Returns:
            List of gateway transactions
        """
        provider = await get_payment_provider(method)
        
        # Note: This would call the gateway's transaction listing API
        # For now, returning mock data
        # In production, implement proper API call
        
        logger.info(f"Fetching {method} transactions from {start_date} to {end_date}")
        
        # Mock implementation
        return []
    
    async def get_order_transactions(
        self,
        start_date: datetime,
        end_date: datetime,
    ) -> List[Dict[str, Any]]:
        """
        Fetch order transactions from database.
        
        Args:
            start_date: Start date
            end_date: End date
            
        Returns:
            List of order transactions
        """
        from apps.orders.models import Order
        from apps.orders.repository import OrderRepository
        
        order_repo = OrderRepository(self.db)
        orders = await order_repo.get_orders_by_date_range(start_date, end_date)
        
        transactions = []
        for order in orders:
            if order.payment_transaction_id:
                transactions.append({
                    "order_id": order.id,
                    "order_number": order.order_number,
                    "amount": order.total,
                    "status": order.payment_status,
                    "transaction_id": order.payment_transaction_id,
                    "payment_method": order.payment_method,
                    "date": order.created_at,
                })
        
        return transactions
    
    async def reconcile(
        self,
        method: str,
        start_date: datetime,
        end_date: datetime,
    ) -> List[ReconciledTransaction]:
        """
        Reconcile gateway transactions with orders.
        
        Args:
            method: Payment method
            start_date: Start date
            end_date: End date
            
        Returns:
            List of reconciled transactions
        """
        # Get transactions from both sources
        gateway_txns = await self.get_gateway_transactions(method, start_date, end_date)
        order_txns = await self.get_order_transactions(start_date, end_date)
        
        # Create maps for easy lookup
        order_by_txn_id = {t["transaction_id"]: t for t in order_txns if t.get("transaction_id")}
        
        reconciled = []
        
        # Match gateway transactions
        for gateway_txn in gateway_txns:
            txn_id = gateway_txn.get("transaction_id")
            order_txn = order_by_txn_id.get(txn_id)
            
            if order_txn:
                # Check if amounts match
                gateway_amount = Decimal(str(gateway_txn.get("amount", 0)))
                order_amount = Decimal(str(order_txn.get("amount", 0)))
                
                if gateway_amount == order_amount:
                    status = ReconciliationStatus.MATCHED
                    discrepancy = None
                    notes = "Amounts match"
                else:
                    status = ReconciliationStatus.MISMATCHED
                    discrepancy = gateway_amount - order_amount
                    notes = f"Amount mismatch: Gateway={gateway_amount}, Order={order_amount}"
            else:
                status = ReconciliationStatus.EXTRA
                discrepancy = None
                notes = "No matching order found"
            
            reconciled.append(ReconciledTransaction(
                gateway_transaction_id=txn_id,
                gateway_amount=Decimal(str(gateway_txn.get("amount", 0))),
                gateway_status=gateway_txn.get("status", "unknown"),
                gateway_date=gateway_txn.get("date", datetime.utcnow()),
                order_id=order_txn.get("order_id") if order_txn else None,
                order_amount=Decimal(str(order_txn.get("amount", 0))) if order_txn else None,
                order_status=order_txn.get("status") if order_txn else None,
                status=status,
                discrepancy=discrepancy,
                notes=notes,
            ))
        
        # Find orders with no matching gateway transaction
        gateway_txn_ids = {t["transaction_id"] for t in gateway_txns}
        for order_txn in order_txns:
            if order_txn.get("transaction_id") not in gateway_txn_ids:
                reconciled.append(ReconciledTransaction(
                    gateway_transaction_id=order_txn.get("transaction_id", "unknown"),
                    gateway_amount=Decimal(str(order_txn.get("amount", 0))),
                    gateway_status="unknown",
                    gateway_date=order_txn.get("date", datetime.utcnow()),
                    order_id=order_txn.get("order_id"),
                    order_amount=Decimal(str(order_txn.get("amount", 0))),
                    order_status=order_txn.get("status"),
                    status=ReconciliationStatus.MISSING,
                    notes="No matching gateway transaction",
                ))
        
        return reconciled
    
    async def generate_reconciliation_report(
        self,
        start_date: datetime,
        end_date: datetime,
    ) -> Dict[str, Any]:
        """
        Generate comprehensive reconciliation report.
        
        Args:
            start_date: Start date
            end_date: End date
            
        Returns:
            Reconciliation report
        """
        methods = ["chapa", "telebirr", "cbe_birr"]
        all_reconciled = []
        
        for method in methods:
            try:
                reconciled = await self.reconcile(method, start_date, end_date)
                all_reconciled.extend(reconciled)
            except Exception as e:
                logger.error(f"Reconciliation failed for {method}: {e}")
        
        # Calculate statistics
        total_gateway_amount = sum(r.gateway_amount for r in all_reconciled)
        total_order_amount = sum(r.order_amount for r in all_reconciled if r.order_amount)
        
        matched = [r for r in all_reconciled if r.status == ReconciliationStatus.MATCHED]
        mismatched = [r for r in all_reconciled if r.status == ReconciliationStatus.MISMATCHED]
        missing = [r for r in all_reconciled if r.status == ReconciliationStatus.MISSING]
        extra = [r for r in all_reconciled if r.status == ReconciliationStatus.EXTRA]
        
        return {
            "period": {
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
            },
            "summary": {
                "total_transactions": len(all_reconciled),
                "total_gateway_amount": float(total_gateway_amount),
                "total_order_amount": float(total_order_amount),
                "discrepancy": float(total_gateway_amount - total_order_amount),
            },
            "breakdown": {
                "matched": {
                    "count": len(matched),
                    "total_amount": float(sum(r.gateway_amount for r in matched)),
                },
                "mismatched": {
                    "count": len(mismatched),
                    "total_amount": float(sum(r.gateway_amount for r in mismatched)),
                },
                "missing": {
                    "count": len(missing),
                    "total_amount": float(sum(r.order_amount for r in missing if r.order_amount)),
                },
                "extra": {
                    "count": len(extra),
                    "total_amount": float(sum(r.gateway_amount for r in extra)),
                },
            },
            "transactions": [self._transaction_to_dict(t) for t in all_reconciled],
        }
    
    def _transaction_to_dict(self, t: ReconciledTransaction) -> Dict[str, Any]:
        """Convert reconciled transaction to dictionary."""
        return {
            "gateway_transaction_id": t.gateway_transaction_id,
            "gateway_amount": float(t.gateway_amount),
            "gateway_status": t.gateway_status,
            "gateway_date": t.gateway_date.isoformat(),
            "order_id": t.order_id,
            "order_amount": float(t.order_amount) if t.order_amount else None,
            "order_status": t.order_status,
            "status": t.status.value,
            "discrepancy": float(t.discrepancy) if t.discrepancy else None,
            "notes": t.notes,
        }


async def reconcile_payments(
    db,
    start_date: datetime,
    end_date: datetime,
) -> Dict[str, Any]:
    """Convenience function to reconcile payments."""
    reconciler = PaymentReconciliation(db)
    return await reconciler.generate_reconciliation_report(start_date, end_date)


__all__ = [
    "PaymentReconciliation",
    "ReconciliationStatus",
    "ReconciledTransaction",
    "reconcile_payments",
]