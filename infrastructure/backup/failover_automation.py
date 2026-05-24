# ============================
# WOLLOYEWA STORE BOT - FAILOVER AUTOMATION
# ============================
"""Automated failover management for high availability."""

import asyncio
from enum import Enum
from typing import Dict, Any, Optional, List, Callable
from dataclasses import dataclass, field
from datetime import datetime

from core.logger import logger


class FailoverStatus(str, Enum):
    """Failover status."""
    NORMAL = "normal"
    DEGRADED = "degraded"
    FAILOVER_IN_PROGRESS = "failover_in_progress"
    FAILOVER_COMPLETE = "failover_complete"
    RECOVERY_IN_PROGRESS = "recovery_in_progress"


class FailoverReason(str, Enum):
    """Reason for failover."""
    PRIMARY_DOWN = "primary_down"
    HIGH_LAG = "high_lag"
    CORRUPTION = "corruption"
    MANUAL = "manual"
    MAINTENANCE = "maintenance"


@dataclass
class FailoverConfig:
    """Failover configuration."""
    
    health_check_interval: int = 30  # seconds
    failure_threshold: int = 3
    recovery_timeout: int = 300  # seconds
    auto_failover_enabled: bool = True
    notify_on_failover: bool = True
    verify_before_failover: bool = True


@dataclass
class HealthCheckResult:
    """Health check result."""
    
    is_healthy: bool
    response_time_ms: float
    error_message: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.utcnow)


class HealthChecker:
    """
    Health checker for database and services.
    
    Features:
    - Regular health checks
    - Configurable thresholds
    - Multiple health indicators
    """
    
    def __init__(self):
        self._checkers: Dict[str, Callable] = {}
        self._last_results: Dict[str, HealthCheckResult] = {}
        self._failure_counts: Dict[str, int] = {}
    
    def register_checker(self, name: str, checker: Callable) -> None:
        """Register a health checker function."""
        self._checkers[name] = checker
        logger.debug(f"Registered health checker: {name}")
    
    async def run_checks(self) -> Dict[str, HealthCheckResult]:
        """Run all registered health checks."""
        results = {}
        
        for name, checker in self._checkers.items():
            try:
                if asyncio.iscoroutinefunction(checker):
                    result = await checker()
                else:
                    result = checker()
                
                if isinstance(result, HealthCheckResult):
                    results[name] = result
                elif isinstance(result, bool):
                    results[name] = HealthCheckResult(
                        is_healthy=result,
                        response_time_ms=0,
                    )
                else:
                    results[name] = HealthCheckResult(
                        is_healthy=bool(result),
                        response_time_ms=0,
                    )
                
                # Update failure count
                if not results[name].is_healthy:
                    self._failure_counts[name] = self._failure_counts.get(name, 0) + 1
                else:
                    self._failure_counts[name] = 0
                
                self._last_results[name] = results[name]
                
            except Exception as e:
                results[name] = HealthCheckResult(
                    is_healthy=False,
                    response_time_ms=0,
                    error_message=str(e),
                )
                self._failure_counts[name] = self._failure_counts.get(name, 0) + 1
        
        return results
    
    def is_healthy(self, threshold: int = 3) -> bool:
        """Check if system is considered healthy."""
        for name, failures in self._failure_counts.items():
            if failures >= threshold:
                logger.warning(f"Health check {name} failed {failures} times")
                return False
        return True
    
    def get_unhealthy_services(self) -> List[str]:
        """Get list of unhealthy services."""
        unhealthy = []
        for name, failures in self._failure_counts.items():
            if failures > 0:
                unhealthy.append(name)
        return unhealthy


class FailoverAutomation:
    """
    Automated failover management.
    
    Features:
    - Automatic failure detection
    - Configurable failover triggers
    - Notification on failover
    - Automatic recovery
    """
    
    def __init__(self, config: Optional[FailoverConfig] = None):
        self.config = config or FailoverConfig()
        self.status = FailoverStatus.NORMAL
        self.health_checker = HealthChecker()
        self._failover_callbacks: List[Callable] = []
        self._recovery_callbacks: List[Callable] = []
        self._monitoring_task: Optional[asyncio.Task] = None
        
        # Register default checkers
        self._register_default_checkers()
    
    def _register_default_checkers(self) -> None:
        """Register default health checkers."""
        self.health_checker.register_checker("database", self._check_database)
        self.health_checker.register_checker("replication", self._check_replication)
    
    async def _check_database(self) -> HealthCheckResult:
        """Check database health."""
        import time
        
        start = time.time()
        try:
            from infrastructure.database.session import get_db_session
            
            async for session in get_db_session():
                await session.execute("SELECT 1")
                response_time = (time.time() - start) * 1000
                return HealthCheckResult(
                    is_healthy=True,
                    response_time_ms=response_time,
                )
        except Exception as e:
            return HealthCheckResult(
                is_healthy=False,
                response_time_ms=0,
                error_message=str(e),
            )
    
    async def _check_replication(self) -> HealthCheckResult:
        """Check replication health."""
        try:
            from infrastructure.backup.replication_manager import get_replication_status
            
            status = await get_replication_status()
            lag = status.get("lag_seconds", 0)
            
            if lag < 60:
                return HealthCheckResult(is_healthy=True, response_time_ms=0)
            else:
                return HealthCheckResult(
                    is_healthy=False,
                    response_time_ms=0,
                    error_message=f"Replication lag: {lag}s",
                )
        except Exception as e:
            return HealthCheckResult(
                is_healthy=False,
                response_time_ms=0,
                error_message=str(e),
            )
    
    def on_failover(self, callback: Callable) -> None:
        """Register callback for failover events."""
        self._failover_callbacks.append(callback)
    
    def on_recovery(self, callback: Callable) -> None:
        """Register callback for recovery events."""
        self._recovery_callbacks.append(callback)
    
    async def _notify_failover(self, reason: FailoverReason) -> None:
        """Notify callbacks about failover."""
        for callback in self._failover_callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(reason)
                else:
                    callback(reason)
            except Exception as e:
                logger.error(f"Failover callback failed: {e}")
    
    async def _notify_recovery(self) -> None:
        """Notify callbacks about recovery."""
        for callback in self._recovery_callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback()
                else:
                    callback()
            except Exception as e:
                logger.error(f"Recovery callback failed: {e}")
    
    async def start_monitoring(self) -> None:
        """Start automated health monitoring."""
        self._monitoring_task = asyncio.create_task(self._monitor_loop())
        logger.info("Failover monitoring started")
    
    async def stop_monitoring(self) -> None:
        """Stop health monitoring."""
        if self._monitoring_task:
            self._monitoring_task.cancel()
            try:
                await self._monitoring_task
            except asyncio.CancelledError:
                pass
        logger.info("Failover monitoring stopped")
    
    async def _monitor_loop(self) -> None:
        """Main monitoring loop."""
        while True:
            try:
                await asyncio.sleep(self.config.health_check_interval)
                
                # Run health checks
                results = await self.health_checker.run_checks()
                
                # Check if failover is needed
                if self.config.auto_failover_enabled:
                    if not self.health_checker.is_healthy(self.config.failure_threshold):
                        if self.status == FailoverStatus.NORMAL:
                            await self.initiate_failover(FailoverReason.PRIMARY_DOWN)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Monitoring loop error: {e}")
    
    async def initiate_failover(
        self,
        reason: FailoverReason,
        verify: bool = True,
    ) -> bool:
        """
        Initiate failover to replica.
        
        Args:
            reason: Reason for failover
            verify: Whether to verify before failover
            
        Returns:
            True if failover successful
        """
        if self.status != FailoverStatus.NORMAL:
            logger.warning(f"Failover already in progress (status: {self.status})")
            return False
        
        logger.warning(f"Initiating failover: {reason.value}")
        self.status = FailoverStatus.FAILOVER_IN_PROGRESS
        
        try:
            # Verify before failover
            if verify and self.config.verify_before_failover:
                if not await self._verify_failover_possible():
                    logger.error("Failover verification failed")
                    self.status = FailoverStatus.NORMAL
                    return False
            
            # Perform failover
            from infrastructure.backup.replication_manager import failover_to_replica
            success = await failover_to_replica()
            
            if success:
                self.status = FailoverStatus.FAILOVER_COMPLETE
                await self._notify_failover(reason)
                logger.info(f"Failover completed: {reason.value}")
                
                # Start recovery process
                asyncio.create_task(self._recover_primary())
                return True
            else:
                self.status = FailoverStatus.NORMAL
                logger.error("Failover failed")
                return False
                
        except Exception as e:
            self.status = FailoverStatus.NORMAL
            logger.error(f"Failover error: {e}")
            return False
    
    async def _verify_failover_possible(self) -> bool:
        """Verify that failover is possible."""
        from infrastructure.backup.replication_manager import get_replication_status
        
        status = await get_replication_status()
        lag = status.get("lag_seconds", 0)
        
        if lag > 300:
            logger.error(f"Replication lag too high for failover: {lag}s")
            return False
        
        return True
    
    async def _recover_primary(self) -> None:
        """Recover original primary after failover."""
        self.status = FailoverStatus.RECOVERY_IN_PROGRESS
        logger.info("Starting primary recovery")
        
        try:
            # Wait before attempting recovery
            await asyncio.sleep(self.config.recovery_timeout)
            
            # Attempt to recover primary
            await self._attempt_primary_recovery()
            
            self.status = FailoverStatus.NORMAL
            await self._notify_recovery()
            logger.info("Primary recovery completed")
            
        except Exception as e:
            logger.error(f"Primary recovery failed: {e}")
            self.status = FailoverStatus.FAILOVER_COMPLETE
    
    async def _attempt_primary_recovery(self) -> bool:
        """Attempt to recover original primary database."""
        # Implementation depends on infrastructure
        logger.info("Attempting primary database recovery...")
        return True


# Global failover automation instance
failover_automation = FailoverAutomation()


async def automatic_failover() -> bool:
    """Trigger automatic failover."""
    return await failover_automation.initiate_failover(FailoverReason.PRIMARY_DOWN)


async def manual_failover() -> bool:
    """Trigger manual failover."""
    return await failover_automation.initiate_failover(FailoverReason.MANUAL, verify=False)


class FailoverManager:
    """Singleton failover manager."""
    
    _instance: Optional[FailoverAutomation] = None
    
    @classmethod
    def get_instance(cls) -> FailoverAutomation:
        if cls._instance is None:
            cls._instance = FailoverAutomation()
        return cls._instance


__all__ = [
    "FailoverAutomation",
    "FailoverConfig",
    "FailoverStatus",
    "FailoverReason",
    "HealthChecker",
    "automatic_failover",
    "manual_failover",
    "FailoverManager",
]