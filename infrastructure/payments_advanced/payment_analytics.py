# ============================
# WOLLOYEWA STORE BOT - PAYMENT ANALYTICS
# ============================
"""Payment analytics and insights for transaction monitoring."""

from datetime import datetime, timedelta
from decimal import Decimal
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field

from core.logger import logger
from infrastructure.payments.base import PaymentStatus


@dataclass
class PaymentMetrics:
    """Payment metrics summary."""
    
    total_transactions: int = 0
    total_volume: Decimal = Decimal(0)
    successful_transactions: int = 0
    successful_volume: Decimal = Decimal(0)
    failed_transactions: int = 0
    failed_volume: Decimal = Decimal(0)
    refunded_transactions: int = 0
    refunded_volume: Decimal = Decimal(0)
    pending_transactions: int = 0
    pending_volume: Decimal = Decimal(0)
    success_rate: float = 0.0
    average_transaction_value: Decimal = Decimal(0)
    
    def calculate_rates(self) -> None:
        """Calculate derived metrics."""
        if self.total_transactions > 0:
            self.success_rate = (self.successful_transactions / self.total_transactions) * 100
            self.average_transaction_value = self.total_volume / self.total_transactions


class PaymentAnalytics:
    """
    Payment analytics service.
    
    Features:
    - Transaction metrics by time period
    - Payment method performance
    - Success/failure analysis
    - Trend detection
    - Payment insights
    """
    
    def __init__(self, db_session):
        self.db = db_session
    
    async def get_transaction_metrics(
        self,
        start_date: datetime,
        end_date: datetime,
        payment_method: Optional[str] = None,
    ) -> PaymentMetrics:
        """
        Get transaction metrics for a time period.
        
        Args:
            start_date: Start date
            end_date: End date
            payment_method: Filter by payment method
            
        Returns:
            PaymentMetrics object
        """
        # In production, query from database
        # This is a placeholder implementation
        
        metrics = PaymentMetrics()
        
        # Mock data - replace with actual database queries
        # transactions = await self._get_transactions(start_date, end_date, payment_method)
        
        metrics.calculate_rates()
        return metrics
    
    async def get_payment_method_breakdown(
        self,
        start_date: datetime,
        end_date: datetime,
    ) -> List[Dict[str, Any]]:
        """
        Get payment method performance breakdown.
        
        Args:
            start_date: Start date
            end_date: End date
            
        Returns:
            List of payment method metrics
        """
        methods = ["chapa", "telebirr", "cbe_birr", "cash_on_delivery"]
        breakdown = []
        
        for method in methods:
            metrics = await self.get_transaction_metrics(start_date, end_date, method)
            breakdown.append({
                "method": method,
                "transactions": metrics.total_transactions,
                "volume": float(metrics.total_volume),
                "success_rate": metrics.success_rate,
                "average_value": float(metrics.average_transaction_value),
            })
        
        return breakdown
    
    async def get_daily_transaction_trends(
        self,
        days: int = 30,
    ) -> List[Dict[str, Any]]:
        """
        Get daily transaction trends.
        
        Args:
            days: Number of days to analyze
            
        Returns:
            List of daily metrics
        """
        trends = []
        end_date = datetime.utcnow()
        
        for i in range(days):
            day_start = end_date - timedelta(days=i+1)
            day_end = end_date - timedelta(days=i)
            
            metrics = await self.get_transaction_metrics(day_start, day_end)
            
            trends.append({
                "date": day_start.strftime("%Y-%m-%d"),
                "transactions": metrics.total_transactions,
                "volume": float(metrics.total_volume),
                "success_rate": metrics.success_rate,
            })
        
        return trends
    
    async def get_failure_analysis(
        self,
        start_date: datetime,
        end_date: datetime,
    ) -> Dict[str, Any]:
        """
        Analyze payment failures.
        
        Args:
            start_date: Start date
            end_date: End date
            
        Returns:
            Failure analysis report
        """
        # Get failed transactions
        # In production, query from database with failure reasons
        failed_transactions = []  # Placeholder
        
        failure_reasons = {}
        failure_by_method = {}
        
        for tx in failed_transactions:
            reason = tx.get("failure_reason", "unknown")
            method = tx.get("payment_method", "unknown")
            
            failure_reasons[reason] = failure_reasons.get(reason, 0) + 1
            failure_by_method[method] = failure_by_method.get(method, 0) + 1
        
        return {
            "total_failures": len(failed_transactions),
            "failure_rate": 0.0,  # Calculate from total transactions
            "failure_reasons": failure_reasons,
            "failure_by_method": failure_by_method,
            "top_failure_reasons": sorted(
                failure_reasons.items(),
                key=lambda x: x[1],
                reverse=True
            )[:5],
        }
    
    async def get_payment_insights(self) -> Dict[str, Any]:
        """
        Generate payment insights and recommendations.
        
        Returns:
            Insights dictionary
        """
        now = datetime.utcnow()
        last_30_days = now - timedelta(days=30)
        
        # Get current period metrics
        current = await self.get_transaction_metrics(last_30_days, now)
        
        # Get previous period metrics for comparison
        previous_start = last_30_days - timedelta(days=30)
        previous = await self.get_transaction_metrics(previous_start, last_30_days)
        
        # Calculate changes
        transaction_change = 0
        if previous.total_transactions > 0:
            transaction_change = ((current.total_transactions - previous.total_transactions) / previous.total_transactions) * 100
        
        volume_change = 0
        if previous.total_volume > 0:
            volume_change = float(((current.total_volume - previous.total_volume) / previous.total_volume) * 100)
        
        success_rate_change = current.success_rate - previous.success_rate
        
        # Generate insights
        insights = []
        
        if transaction_change > 10:
            insights.append({
                "type": "positive",
                "message": f"Transaction volume increased by {transaction_change:.1f}% compared to previous period",
            })
        elif transaction_change < -10:
            insights.append({
                "type": "warning",
                "message": f"Transaction volume decreased by {abs(transaction_change):.1f}% compared to previous period",
            })
        
        if success_rate_change > 5:
            insights.append({
                "type": "positive",
                "message": f"Payment success rate improved by {success_rate_change:.1f}%",
            })
        elif success_rate_change < -5:
            insights.append({
                "type": "warning",
                "message": f"Payment success rate declined by {abs(success_rate_change):.1f}%. Check for issues.",
            })
        
        return {
            "period": {
                "start": last_30_days.isoformat(),
                "end": now.isoformat(),
            },
            "current_metrics": {
                "transactions": current.total_transactions,
                "volume": float(current.total_volume),
                "success_rate": current.success_rate,
                "avg_transaction": float(current.average_transaction_value),
            },
            "changes": {
                "transaction_change": round(transaction_change, 1),
                "volume_change": round(volume_change, 1),
                "success_rate_change": round(success_rate_change, 1),
            },
            "insights": insights,
        }


async def analyze_payments(
    db,
    start_date: datetime,
    end_date: datetime,
) -> Dict[str, Any]:
    """Analyze payments for a date range."""
    analytics = PaymentAnalytics(db)
    metrics = await analytics.get_transaction_metrics(start_date, end_date)
    
    return {
        "period": {
            "start": start_date.isoformat(),
            "end": end_date.isoformat(),
        },
        "total_transactions": metrics.total_transactions,
        "total_volume": float(metrics.total_volume),
        "successful_transactions": metrics.successful_transactions,
        "failed_transactions": metrics.failed_transactions,
        "success_rate": metrics.success_rate,
        "average_transaction_value": float(metrics.average_transaction_value),
    }


async def get_payment_trends(
    db,
    days: int = 30,
) -> List[Dict[str, Any]]:
    """Get payment trends for the last N days."""
    analytics = PaymentAnalytics(db)
    return await analytics.get_daily_transaction_trends(days)


async def get_payment_insights(db) -> Dict[str, Any]:
    """Get payment insights and recommendations."""
    analytics = PaymentAnalytics(db)
    return await analytics.get_payment_insights()


__all__ = [
    "PaymentAnalytics",
    "PaymentMetrics",
    "analyze_payments",
    "get_payment_trends",
    "get_payment_insights",
]