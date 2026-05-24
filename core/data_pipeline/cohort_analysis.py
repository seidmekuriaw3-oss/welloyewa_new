# ============================
# WOLLOYEWA STORE BOT - COHORT ANALYSIS
# ============================
"""Cohort analysis for user retention and lifetime value tracking."""

from enum import Enum
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from collections import defaultdict

from core.logger import logger


class CohortType(str, Enum):
    """Types of cohort grouping."""
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"


@dataclass
class Cohort:
    """Represents a user cohort."""
    
    cohort_id: str
    name: str
    start_date: datetime
    end_date: datetime
    user_count: int = 0
    metrics: Dict[str, Dict[int, float]] = field(default_factory=dict)


@dataclass
class RetentionData:
    """Retention data for a cohort."""
    
    cohort_period: str
    period_number: int  # Week 1, Week 2, etc.
    users_acquired: int
    users_returned: int
    retention_rate: float  # Percentage


class CohortAnalysis:
    """
    Cohort analysis for user behavior tracking.
    
    Features:
    - User retention by cohort
    - Customer lifetime value (LTV) by cohort
    - Revenue analysis by cohort
    - Engagement metrics tracking
    """
    
    def __init__(self):
        self._cohorts: Dict[str, Cohort] = {}
        self._user_cohorts: Dict[int, Tuple[str, datetime]] = {}  # user_id -> (cohort_id, join_date)
        self._user_activity: Dict[int, List[Tuple[datetime, float]]] = defaultdict(list)  # user_id -> [(date, revenue)]
    
    def create_cohort(
        self,
        name: str,
        start_date: datetime,
        end_date: datetime,
        cohort_id: Optional[str] = None,
    ) -> Cohort:
        """
        Create a new user cohort.
        
        Args:
            name: Cohort name
            start_date: Start date of cohort period
            end_date: End date of cohort period
            cohort_id: Optional custom ID
            
        Returns:
            Created Cohort object
        """
        cohort_id = cohort_id or f"cohort_{start_date.strftime('%Y%m%d')}"
        
        cohort = Cohort(
            cohort_id=cohort_id,
            name=name,
            start_date=start_date,
            end_date=end_date,
        )
        
        self._cohorts[cohort_id] = cohort
        logger.info(f"Created cohort: {name} ({start_date.date()} to {end_date.date()})")
        
        return cohort
    
    def assign_user_to_cohort(self, user_id: int, join_date: datetime) -> Optional[str]:
        """
        Assign a user to a cohort based on their join date.
        
        Args:
            user_id: User ID
            join_date: User's join/registration date
            
        Returns:
            Cohort ID user was assigned to
        """
        for cohort_id, cohort in self._cohorts.items():
            if cohort.start_date <= join_date <= cohort.end_date:
                self._user_cohorts[user_id] = (cohort_id, join_date)
                cohort.user_count += 1
                logger.debug(f"User {user_id} assigned to cohort {cohort_id}")
                return cohort_id
        
        return None
    
    def record_user_activity(
        self,
        user_id: int,
        activity_date: datetime,
        revenue: float = 0.0,
    ) -> None:
        """
        Record user activity for retention and LTV calculation.
        
        Args:
            user_id: User ID
            activity_date: Date of activity
            revenue: Revenue generated (if any)
        """
        self._user_activity[user_id].append((activity_date, revenue))
    
    def calculate_retention(
        self,
        cohort_id: str,
        weeks: int = 12,
    ) -> List[RetentionData]:
        """
        Calculate retention rates for a cohort.
        
        Args:
            cohort_id: Cohort ID
            weeks: Number of weeks to analyze
            
        Returns:
            List of retention data by period
        """
        cohort = self._cohorts.get(cohort_id)
        if not cohort:
            return []
        
        # Get users in this cohort
        cohort_users = [
            user_id for user_id, (cid, _) in self._user_cohorts.items()
            if cid == cohort_id
        ]
        
        if not cohort_users:
            return []
        
        retention_data = []
        
        # Calculate retention for each week
        for week in range(1, weeks + 1):
            period_start = cohort.start_date + timedelta(days=(week - 1) * 7)
            period_end = period_start + timedelta(days=6)
            
            # Count users active during this period
            active_users = 0
            for user_id in cohort_users:
                user_activities = self._user_activity.get(user_id, [])
                for activity_date, _ in user_activities:
                    if period_start <= activity_date <= period_end:
                        active_users += 1
                        break
            
            retention_rate = (active_users / cohort.user_count * 100) if cohort.user_count > 0 else 0
            
            retention_data.append(RetentionData(
                cohort_period=cohort.name,
                period_number=week,
                users_acquired=cohort.user_count,
                users_returned=active_users,
                retention_rate=round(retention_rate, 2),
            ))
        
        return retention_data
    
    def calculate_lifetime_value(
        self,
        cohort_id: str,
        weeks: int = 12,
    ) -> Dict[int, float]:
        """
        Calculate Customer Lifetime Value (LTV) for a cohort.
        
        Args:
            cohort_id: Cohort ID
            weeks: Number of weeks to analyze
            
        Returns:
            Dictionary mapping week number to cumulative LTV
        """
        cohort = self._cohorts.get(cohort_id)
        if not cohort:
            return {}
        
        # Get users in this cohort
        cohort_users = [
            user_id for user_id, (cid, _) in self._user_cohorts.items()
            if cid == cohort_id
        ]
        
        if not cohort_users:
            return {}
        
        ltv_by_week = {}
        cumulative_revenue = 0.0
        
        for week in range(1, weeks + 1):
            period_start = cohort.start_date + timedelta(days=(week - 1) * 7)
            period_end = period_start + timedelta(days=6)
            
            week_revenue = 0.0
            for user_id in cohort_users:
                user_activities = self._user_activity.get(user_id, [])
                for activity_date, revenue in user_activities:
                    if period_start <= activity_date <= period_end:
                        week_revenue += revenue
            
            cumulative_revenue += week_revenue
            avg_ltv = cumulative_revenue / cohort.user_count if cohort.user_count > 0 else 0
            ltv_by_week[week] = round(avg_ltv, 2)
        
        return ltv_by_week
    
    def get_cohort_performance(
        self,
        cohort_id: str,
    ) -> Dict[str, Any]:
        """
        Get comprehensive performance metrics for a cohort.
        
        Args:
            cohort_id: Cohort ID
            
        Returns:
            Dictionary with performance metrics
        """
        cohort = self._cohorts.get(cohort_id)
        if not cohort:
            return {"error": "Cohort not found"}
        
        retention = self.calculate_retention(cohort_id)
        ltv = self.calculate_lifetime_value(cohort_id)
        
        # Calculate average retention
        avg_retention = sum(r.retention_rate for r in retention) / len(retention) if retention else 0
        
        # Calculate total revenue
        total_revenue = 0.0
        for user_id, (cid, _) in self._user_cohorts.items():
            if cid == cohort_id:
                user_activities = self._user_activity.get(user_id, [])
                total_revenue += sum(revenue for _, revenue in user_activities)
        
        return {
            "cohort_id": cohort.cohort_id,
            "cohort_name": cohort.name,
            "period": f"{cohort.start_date.date()} to {cohort.end_date.date()}",
            "user_count": cohort.user_count,
            "total_revenue": round(total_revenue, 2),
            "average_revenue_per_user": round(total_revenue / cohort.user_count, 2) if cohort.user_count > 0 else 0,
            "average_retention_rate": round(avg_retention, 2),
            "week_4_retention": retention[3].retention_rate if len(retention) > 3 else 0,
            "week_8_retention": retention[7].retention_rate if len(retention) > 7 else 0,
            "week_12_retention": retention[11].retention_rate if len(retention) > 11 else 0,
            "ltv_week_4": ltv.get(4, 0),
            "ltv_week_8": ltv.get(8, 0),
            "ltv_week_12": ltv.get(12, 0),
        }
    
    def compare_cohorts(
        self,
        cohort_ids: List[str],
    ) -> Dict[str, Any]:
        """
        Compare multiple cohorts.
        
        Args:
            cohort_ids: List of cohort IDs to compare
            
        Returns:
            Comparison metrics for all cohorts
        """
        comparison = {}
        
        for cohort_id in cohort_ids:
            comparison[cohort_id] = self.get_cohort_performance(cohort_id)
        
        return comparison
    
    def generate_cohort_report(self) -> Dict[str, Any]:
        """
        Generate a complete cohort analysis report.
        
        Returns:
            Comprehensive cohort analysis report
        """
        report = {
            "total_cohorts": len(self._cohorts),
            "total_users_analyzed": len(self._user_cohorts),
            "cohorts": [],
        }
        
        for cohort_id in self._cohorts:
            performance = self.get_cohort_performance(cohort_id)
            report["cohorts"].append(performance)
        
        # Sort by cohort date
        report["cohorts"].sort(key=lambda x: x.get("period", ""))
        
        return report


# Global cohort analysis instance
cohort_analysis = CohortAnalysis()


def perform_cohort_analysis(
    start_date: datetime,
    end_date: datetime,
    cohort_type: CohortType = CohortType.WEEKLY,
) -> Dict[str, Any]:
    """
    Perform cohort analysis for a date range.
    
    Args:
        start_date: Analysis start date
        end_date: Analysis end date
        cohort_type: Type of cohort grouping
        
    Returns:
        Cohort analysis report
    """
    # Create cohorts based on type
    current = start_date
    
    if cohort_type == CohortType.WEEKLY:
        delta = timedelta(days=7)
        while current <= end_date:
            cohort_end = min(current + delta - timedelta(days=1), end_date)
            cohort_analysis.create_cohort(
                name=f"Week of {current.strftime('%Y-%m-%d')}",
                start_date=current,
                end_date=cohort_end,
            )
            current = cohort_end + timedelta(days=1)
    
    elif cohort_type == CohortType.MONTHLY:
        while current <= end_date:
            # Get last day of month
            if current.month == 12:
                next_month = current.replace(year=current.year + 1, month=1, day=1)
            else:
                next_month = current.replace(month=current.month + 1, day=1)
            cohort_end = next_month - timedelta(days=1)
            cohort_end = min(cohort_end, end_date)
            
            cohort_analysis.create_cohort(
                name=f"{current.strftime('%B %Y')}",
                start_date=current,
                end_date=cohort_end,
            )
            current = next_month
    
    return cohort_analysis.generate_cohort_report()


def get_user_retention(
    cohort_id: str,
    weeks: int = 12,
) -> List[RetentionData]:
    """Get retention data for a cohort."""
    return cohort_analysis.calculate_retention(cohort_id, weeks)


def get_lifetime_value(
    cohort_id: str,
    weeks: int = 12,
) -> Dict[int, float]:
    """Get LTV data for a cohort."""
    return cohort_analysis.calculate_lifetime_value(cohort_id, weeks)


__all__ = [
    "CohortAnalysis",
    "CohortType",
    "Cohort",
    "RetentionData",
    "cohort_analysis",
    "perform_cohort_analysis",
    "get_user_retention",
    "get_lifetime_value",
]