# ============================
# WOLLOYEWA STORE BOT - SLA MONITOR
# ============================
"""Service Level Agreement (SLA) monitoring for support tickets."""

from enum import Enum
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from datetime import datetime, timedelta

from core.logger import logger


class SLAMetric(str, Enum):
    """SLA metrics for support."""
    FIRST_RESPONSE_TIME = "first_response_time"
    RESOLUTION_TIME = "resolution_time"
    RESPONSE_RATE = "response_rate"
    CUSTOMER_SATISFACTION = "customer_satisfaction"


@dataclass
class SLAViolation:
    """SLA violation record."""
    
    ticket_id: int
    metric: SLAMetric
    target_minutes: int
    actual_minutes: float
    violated_at: datetime
    severity: str = "warning"


@dataclass
class SLATracker:
    """SLA tracking for a ticket."""
    
    ticket_id: int
    created_at: datetime
    first_response_at: Optional[datetime] = None
    resolved_at: Optional[datetime] = None
    first_response_target: int = 60  # minutes
    resolution_target: int = 480  # 8 hours
    violations: List[SLAViolation] = field(default_factory=list)


class SLAMonitor:
    """
    SLA monitor for support tickets.
    
    Features:
    - First response time tracking
    - Resolution time tracking
    - SLA violation detection
    - Reporting and alerts
    """
    
    def __init__(self):
        self._ticket_sla: Dict[int, SLATracker] = {}
        self._violations: List[SLAViolation] = []
        
        # Default SLA targets
        self.first_response_target = 60  # minutes
        self.resolution_target = 480  # minutes (8 hours)
        self.critical_response_target = 30  # minutes for high priority
        self.critical_resolution_target = 240  # 4 hours for high priority
    
    def start_tracking(self, ticket_id: int, priority: str = "normal") -> None:
        """
        Start SLA tracking for a ticket.
        
        Args:
            ticket_id: Ticket ID
            priority: Ticket priority
        """
        first_response_target = self.first_response_target
        resolution_target = self.resolution_target
        
        if priority == "high" or priority == "urgent":
            first_response_target = self.critical_response_target
            resolution_target = self.critical_resolution_target
        
        tracker = SLATracker(
            ticket_id=ticket_id,
            created_at=datetime.utcnow(),
            first_response_target=first_response_target,
            resolution_target=resolution_target,
        )
        
        self._ticket_sla[ticket_id] = tracker
        logger.info(f"SLA tracking started for ticket {ticket_id}")
    
    def record_first_response(self, ticket_id: int, response_time: datetime) -> None:
        """
        Record first response time.
        
        Args:
            ticket_id: Ticket ID
            response_time: Time of first response
        """
        tracker = self._ticket_sla.get(ticket_id)
        if not tracker:
            return
        
        tracker.first_response_at = response_time
        
        # Check for violation
        response_minutes = (response_time - tracker.created_at).total_seconds() / 60
        
        if response_minutes > tracker.first_response_target:
            violation = SLAViolation(
                ticket_id=ticket_id,
                metric=SLAMetric.FIRST_RESPONSE_TIME,
                target_minutes=tracker.first_response_target,
                actual_minutes=round(response_minutes, 1),
                violated_at=datetime.utcnow(),
                severity="critical" if response_minutes > tracker.first_response_target * 2 else "warning",
            )
            self._violations.append(violation)
            logger.warning(f"SLA violation: First response time for ticket {ticket_id} exceeded target")
    
    def record_resolution(self, ticket_id: int, resolved_at: datetime) -> None:
        """
        Record ticket resolution time.
        
        Args:
            ticket_id: Ticket ID
            resolved_at: Time of resolution
        """
        tracker = self._ticket_sla.get(ticket_id)
        if not tracker:
            return
        
        tracker.resolved_at = resolved_at
        
        # Check for violation
        resolution_minutes = (resolved_at - tracker.created_at).total_seconds() / 60
        
        if resolution_minutes > tracker.resolution_target:
            violation = SLAViolation(
                ticket_id=ticket_id,
                metric=SLAMetric.RESOLUTION_TIME,
                target_minutes=tracker.resolution_target,
                actual_minutes=round(resolution_minutes, 1),
                violated_at=datetime.utcnow(),
                severity="critical",
            )
            self._violations.append(violation)
            logger.warning(f"SLA violation: Resolution time for ticket {ticket_id} exceeded target")
    
    def check_sla_compliance(self, ticket_id: int) -> Dict[str, Any]:
        """
        Check SLA compliance for a ticket.
        
        Args:
            ticket_id: Ticket ID
            
        Returns:
            Compliance status
        """
        tracker = self._ticket_sla.get(ticket_id)
        if not tracker:
            return {"tracking": False}
        
        now = datetime.utcnow()
        first_response_compliant = True
        resolution_compliant = True
        
        # Check first response compliance
        if not tracker.first_response_at:
            elapsed_minutes = (now - tracker.created_at).total_seconds() / 60
            first_response_compliant = elapsed_minutes <= tracker.first_response_target
            first_response_remaining = max(0, tracker.first_response_target - elapsed_minutes)
        else:
            first_response_remaining = 0
        
        # Check resolution compliance
        if not tracker.resolved_at:
            elapsed_minutes = (now - tracker.created_at).total_seconds() / 60
            resolution_compliant = elapsed_minutes <= tracker.resolution_target
            resolution_remaining = max(0, tracker.resolution_target - elapsed_minutes)
        else:
            resolution_remaining = 0
        
        return {
            "tracking": True,
            "first_response": {
                "compliant": first_response_compliant,
                "target_minutes": tracker.first_response_target,
                "remaining_minutes": round(first_response_remaining, 1),
                "responded": tracker.first_response_at is not None,
            },
            "resolution": {
                "compliant": resolution_compliant,
                "target_minutes": tracker.resolution_target,
                "remaining_minutes": round(resolution_remaining, 1),
                "resolved": tracker.resolved_at is not None,
            },
        }
    
    def get_open_sla_risks(self) -> List[Dict[str, Any]]:
        """
        Get tickets at risk of SLA violation.
        
        Returns:
            List of tickets at risk
        """
        risks = []
        
        for ticket_id, tracker in self._ticket_sla.items():
            if tracker.resolved_at:
                continue
            
            now = datetime.utcnow()
            
            # Check first response risk
            if not tracker.first_response_at:
                elapsed = (now - tracker.created_at).total_seconds() / 60
                if elapsed > tracker.first_response_target * 0.8:  # 80% of target
                    risks.append({
                        "ticket_id": ticket_id,
                        "metric": "first_response",
                        "elapsed_minutes": round(elapsed, 1),
                        "target_minutes": tracker.first_response_target,
                        "risk_level": "high" if elapsed > tracker.first_response_target else "medium",
                    })
            
            # Check resolution risk
            elapsed = (now - tracker.created_at).total_seconds() / 60
            if elapsed > tracker.resolution_target * 0.8:
                risks.append({
                    "ticket_id": ticket_id,
                    "metric": "resolution",
                    "elapsed_minutes": round(elapsed, 1),
                    "target_minutes": tracker.resolution_target,
                    "risk_level": "high" if elapsed > tracker.resolution_target else "medium",
                })
        
        return risks
    
    def get_sla_report(self) -> Dict[str, Any]:
        """
        Get SLA compliance report.
        
        Returns:
            SLA report
        """
        total_tickets = len(self._ticket_sla)
        resolved_tickets = sum(1 for t in self._ticket_sla.values() if t.resolved_at)
        
        first_response_violations = sum(
            1 for v in self._violations
            if v.metric == SLAMetric.FIRST_RESPONSE_TIME
        )
        resolution_violations = sum(
            1 for v in self._violations
            if v.metric == SLAMetric.RESOLUTION_TIME
        )
        
        return {
            "total_tickets_tracked": total_tickets,
            "resolved_tickets": resolved_tickets,
            "first_response_violations": first_response_violations,
            "resolution_violations": resolution_violations,
            "compliance_rate": round(
                (total_tickets - first_response_violations - resolution_violations) / max(total_tickets, 1) * 100,
                1
            ),
            "open_risks": len(self.get_open_sla_risks()),
        }
    
    def stop_tracking(self, ticket_id: int) -> None:
        """Stop SLA tracking for a ticket."""
        if ticket_id in self._ticket_sla:
            del self._ticket_sla[ticket_id]
            logger.info(f"SLA tracking stopped for ticket {ticket_id}")


# Global SLA monitor
sla_monitor = SLAMonitor()


async def monitor_sla(ticket_id: int, priority: str = "normal") -> None:
    """Start SLA monitoring for a ticket."""
    sla_monitor.start_tracking(ticket_id, priority)


async def check_sla_compliance(ticket_id: int) -> Dict[str, Any]:
    """Check SLA compliance for a ticket."""
    return sla_monitor.check_sla_compliance(ticket_id)


async def get_sla_report() -> Dict[str, Any]:
    """Get SLA compliance report."""
    return sla_monitor.get_sla_report()


__all__ = [
    "SLAMonitor",
    "SLAMetric",
    "SLAViolation",
    "SLATracker",
    "sla_monitor",
    "monitor_sla",
    "check_sla_compliance",
    "get_sla_report",
]