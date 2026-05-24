# ============================
# WOLLOYEWA STORE BOT - SLA TRACKER
# ============================
"""Service Level Agreement (SLA) tracking and compliance monitoring."""

import time
from enum import Enum
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from collections import defaultdict, deque

from core.config import settings
from core.logger import logger


class SLAMetric(Enum):
    """SLA metrics to track."""
    UPTIME = "uptime"
    RESPONSE_TIME = "response_time"
    ERROR_RATE = "error_rate"
    THROUGHPUT = "throughput"
    AVAILABILITY = "availability"
    ORDER_FULFILLMENT = "order_fulfillment"
    PAYMENT_SUCCESS = "payment_success"
    CUSTOMER_SATISFACTION = "customer_satisfaction"


class SLAStatus(Enum):
    """SLA compliance status."""
    COMPLIANT = "compliant"
    AT_RISK = "at_risk"
    BREACHED = "breached"
    NOT_TRACKING = "not_tracking"


@dataclass
class SLATarget:
    """SLA target definition."""
    
    metric: SLAMetric
    target_value: float
    comparison: str  # 'gte', 'lte', 'eq'
    time_window_hours: int = 24
    current_value: float = 0.0
    status: SLAStatus = SLAStatus.NOT_TRACKING
    
    def evaluate(self, actual_value: float) -> SLAStatus:
        """Evaluate if actual value meets SLA target."""
        self.current_value = actual_value
        
        if self.comparison == 'gte':
            if actual_value >= self.target_value:
                return SLAStatus.COMPLIANT
            elif actual_value >= self.target_value * 0.9:
                return SLAStatus.AT_RISK
            else:
                return SLAStatus.BREACHED
        elif self.comparison == 'lte':
            if actual_value <= self.target_value:
                return SLAStatus.COMPLIANT
            elif actual_value <= self.target_value * 1.1:
                return SLAStatus.AT_RISK
            else:
                return SLAStatus.BREACHED
        else:
            return SLAStatus.COMPLIANT if actual_value == self.target_value else SLAStatus.BREACHED


@dataclass
class SLARecord:
    """SLA record for historical tracking."""
    
    metric: SLAMetric
    value: float
    status: SLAStatus
    timestamp: datetime = field(default_factory=datetime.utcnow)


class SLATracker:
    """
    Service Level Agreement (SLA) tracker.
    
    Tracks:
    - API response times
    - System uptime
    - Error rates
    - Order fulfillment times
    - Payment success rates
    - Customer satisfaction
    """
    
    def __init__(self):
        self._targets: Dict[SLAMetric, SLATarget] = {}
        self._records: Dict[SLAMetric, deque] = defaultdict(lambda: deque(maxlen=10000))
        self._start_time = time.time()
        self._last_check_time = time.time()
        self._downtime_seconds = 0
        self._total_requests = 0
        self._error_requests = 0
        self._response_times: deque = deque(maxlen=1000)
        
        # Initialize default targets
        self._init_default_targets()
    
    def _init_default_targets(self) -> None:
        """Initialize default SLA targets."""
        self._targets[SLAMetric.UPTIME] = SLATarget(
            metric=SLAMetric.UPTIME,
            target_value=99.9,  # 99.9% uptime
            comparison='gte',
            time_window_hours=720,  # 30 days
        )
        
        self._targets[SLAMetric.RESPONSE_TIME] = SLATarget(
            metric=SLAMetric.RESPONSE_TIME,
            target_value=500,  # 500ms
            comparison='lte',
            time_window_hours=24,
        )
        
        self._targets[SLAMetric.ERROR_RATE] = SLATarget(
            metric=SLAMetric.ERROR_RATE,
            target_value=1.0,  # 1% error rate
            comparison='lte',
            time_window_hours=24,
        )
        
        self._targets[SLAMetric.PAYMENT_SUCCESS] = SLATarget(
            metric=SLAMetric.PAYMENT_SUCCESS,
            target_value=98.0,  # 98% success rate
            comparison='gte',
            time_window_hours=24,
        )
        
        self._targets[SLAMetric.ORDER_FULFILLMENT] = SLATarget(
            metric=SLAMetric.ORDER_FULFILLMENT,
            target_value=95.0,  # 95% fulfilled within time
            comparison='gte',
            time_window_hours=168,  # 7 days
        )
    
    def set_target(self, metric: SLAMetric, target: SLATarget) -> None:
        """Set or update SLA target for a metric."""
        self._targets[metric] = target
        logger.info(f"SLA target set for {metric.value}: {target.target_value} ({target.comparison})")
    
    def record_uptime(self, is_up: bool) -> None:
        """Record system uptime status."""
        current_time = time.time()
        elapsed = current_time - self._last_check_time
        
        if not is_up:
            self._downtime_seconds += elapsed
        
        self._last_check_time = current_time
        
        # Calculate uptime percentage
        total_seconds = current_time - self._start_time
        if total_seconds > 0:
            uptime = ((total_seconds - self._downtime_seconds) / total_seconds) * 100
            self._update_metric(SLAMetric.UPTIME, uptime)
    
    def record_request(self, response_time_ms: float, is_error: bool = False) -> None:
        """Record API request metrics."""
        self._total_requests += 1
        self._response_times.append(response_time_ms)
        
        if is_error:
            self._error_requests += 1
        
        # Update response time SLA (95th percentile)
        if len(self._response_times) > 20:
            sorted_times = sorted(self._response_times)
            percentile_95 = sorted_times[int(len(sorted_times) * 0.95)]
            self._update_metric(SLAMetric.RESPONSE_TIME, percentile_95)
        
        # Update error rate SLA
        if self._total_requests > 0:
            error_rate = (self._error_requests / self._total_requests) * 100
            self._update_metric(SLAMetric.ERROR_RATE, error_rate)
    
    def record_payment(self, success: bool) -> None:
        """Record payment attempt."""
        # This would integrate with payment metrics
        pass
    
    def _update_metric(self, metric: SLAMetric, value: float) -> None:
        """Update metric value and evaluate SLA."""
        if metric not in self._targets:
            return
        
        target = self._targets[metric]
        status = target.evaluate(value)
        
        # Record historical data
        self._records[metric].append(SLARecord(
            metric=metric,
            value=value,
            status=status,
        ))
        
        # Log SLA breaches
        if status == SLAStatus.BREACHED:
            logger.warning(
                f"SLA BREACH: {metric.value} = {value:.2f} "
                f"(target: {target.comparison} {target.target_value})"
            )
        elif status == SLAStatus.AT_RISK:
            logger.info(
                f"SLA AT RISK: {metric.value} = {value:.2f} "
                f"(target: {target.comparison} {target.target_value})"
            )
    
    def get_current_status(self, metric: SLAMetric) -> Optional[SLATarget]:
        """Get current SLA status for a metric."""
        return self._targets.get(metric)
    
    def get_all_status(self) -> Dict[str, Dict[str, Any]]:
        """Get all SLA statuses."""
        statuses = {}
        
        for metric, target in self._targets.items():
            statuses[metric.value] = {
                "target_value": target.target_value,
                "current_value": round(target.current_value, 2),
                "status": target.status.value,
                "comparison": target.comparison,
                "time_window_hours": target.time_window_hours,
            }
        
        return statuses
    
    def get_historical_data(
        self,
        metric: SLAMetric,
        hours: int = 24,
    ) -> List[Dict[str, Any]]:
        """Get historical SLA data for a metric."""
        cutoff = datetime.utcnow() - timedelta(hours=hours)
        
        records = [
            {
                "value": r.value,
                "status": r.status.value,
                "timestamp": r.timestamp.isoformat(),
            }
            for r in self._records.get(metric, [])
            if r.timestamp >= cutoff
        ]
        
        return records
    
    def generate_report(self) -> Dict[str, Any]:
        """Generate SLA compliance report."""
        statuses = self.get_all_status()
        
        # Calculate overall compliance
        compliant = sum(1 for s in statuses.values() if s["status"] == "compliant")
        total = len(statuses)
        compliance_rate = (compliant / total * 100) if total > 0 else 0
        
        # Find breached metrics
        breached = [
            name for name, s in statuses.items()
            if s["status"] == "breached"
        ]
        
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "service": settings.PROJECT_NAME,
            "environment": settings.ENVIRONMENT,
            "compliance_rate": round(compliance_rate, 2),
            "compliant_metrics": compliant,
            "total_metrics": total,
            "breached_metrics": breached,
            "metrics": statuses,
            "uptime_current": self._get_uptime_current(),
        }
    
    def _get_uptime_current(self) -> float:
        """Calculate current uptime percentage."""
        total_seconds = time.time() - self._start_time
        if total_seconds > 0:
            return ((total_seconds - self._downtime_seconds) / total_seconds) * 100
        return 100.0
    
    def reset(self) -> None:
        """Reset all SLA tracking data."""
        self._start_time = time.time()
        self._last_check_time = time.time()
        self._downtime_seconds = 0
        self._total_requests = 0
        self._error_requests = 0
        self._response_times.clear()
        self._records.clear()
        self._init_default_targets()
        logger.info("SLA tracker reset")


# Global SLA tracker instance
sla_tracker = SLATracker()


def track_sla_metric(metric: SLAMetric, value: float) -> None:
    """Convenience function to track an SLA metric."""
    sla_tracker._update_metric(metric, value)


def get_sla_report() -> Dict[str, Any]:
    """Get SLA compliance report."""
    return sla_tracker.generate_report()


__all__ = [
    "SLATracker",
    "SLAMetric",
    "SLAStatus",
    "SLATarget",
    "SLARecord",
    "sla_tracker",
    "track_sla_metric",
    "get_sla_report",
]