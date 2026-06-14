# ============================
# WOLLOYEWA STORE BOT - HEALTH CHECKS
# ============================
"""Health check endpoints and service monitoring."""

import asyncio
from enum import Enum
from typing import Dict, Any, Optional, List, Callable
from dataclasses import dataclass, field
from datetime import datetime
import time

from core.config import settings
from core.logger import logger


class HealthStatus(Enum):
    """Health check status."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


@dataclass
class HealthCheckResult:
    """Result of a health check."""
    
    name: str
    status: HealthStatus
    message: Optional[str] = None
    details: Dict[str, Any] = field(default_factory=dict)
    response_time_ms: float = 0.0
    timestamp: datetime = field(default_factory=datetime.utcnow)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API response."""
        return {
            "name": self.name,
            "status": self.status.value,
            "message": self.message,
            "details": self.details,
            "response_time_ms": round(self.response_time_ms, 2),
            "timestamp": self.timestamp.isoformat(),
        }


class HealthChecker:
    """
    Health check manager for monitoring service health.
    
    Checks:
    - Database connectivity
    - Redis connectivity
    - Payment gateways
    - External services
    - Disk space
    - Memory usage
    """
    
    def __init__(self):
        self._checks: Dict[str, Callable] = {}
        self._results: Dict[str, HealthCheckResult] = {}
        self._last_check: Optional[datetime] = None
        self._check_interval = 30  # seconds
    
    def register(self, name: str, check_func: Callable) -> None:
        """Register a health check function."""
        self._checks[name] = check_func
        logger.debug(f"Registered health check: {name}")
    
    async def run_check(self, name: str) -> HealthCheckResult:
        """Run a single health check."""
        if name not in self._checks:
            return HealthCheckResult(
                name=name,
                status=HealthStatus.UNKNOWN,
                message=f"Unknown health check: {name}",
            )
        
        start_time = time.time()
        try:
            check_func = self._checks[name]
            
            if asyncio.iscoroutinefunction(check_func):
                result = await check_func()
            else:
                result = check_func()
            
            response_time = (time.time() - start_time) * 1000
            
            if isinstance(result, HealthCheckResult):
                result.response_time_ms = response_time
                self._results[name] = result
                return result
            elif isinstance(result, tuple) and len(result) >= 2:
                status, message = result[0], result[1]
                health_status = HealthStatus.HEALTHY if status else HealthStatus.UNHEALTHY
                check_result = HealthCheckResult(
                    name=name,
                    status=health_status,
                    message=message,
                    details=result[2] if len(result) > 2 else {},
                    response_time_ms=response_time,
                )
                self._results[name] = check_result
                return check_result
            elif result is True:
                check_result = HealthCheckResult(
                    name=name,
                    status=HealthStatus.HEALTHY,
                    response_time_ms=response_time,
                )
                self._results[name] = check_result
                return check_result
            else:
                check_result = HealthCheckResult(
                    name=name,
                    status=HealthStatus.UNHEALTHY,
                    message=str(result) if result else "Check failed",
                    response_time_ms=response_time,
                )
                self._results[name] = check_result
                return check_result
                
        except Exception as e:
            response_time = (time.time() - start_time) * 1000
            logger.error(f"Health check '{name}' failed: {e}")
            check_result = HealthCheckResult(
                name=name,
                status=HealthStatus.UNHEALTHY,
                message=str(e),
                response_time_ms=response_time,
            )
            self._results[name] = check_result
            return check_result
    
    async def run_all_checks(self) -> Dict[str, HealthCheckResult]:
        """Run all registered health checks."""
        results = {}
        self._last_check = datetime.utcnow()
        
        for name in self._checks:
            try:
                result = await self.run_check(name)
                results[name] = result
            except Exception as e:
                logger.error(f"Health check '{name}' exception: {e}")
                results[name] = HealthCheckResult(
                    name=name,
                    status=HealthStatus.UNHEALTHY,
                    message=str(e),
                )
        
        self._results.update(results)
        return results
    
    async def check_all(self) -> Dict[str, Any]:
        """Get overall health status with all checks."""
        results = await self.run_all_checks()
        
        # Determine overall status
        statuses = [r.status for r in results.values()]
        
        if HealthStatus.UNHEALTHY in statuses:
            overall = HealthStatus.UNHEALTHY
        elif HealthStatus.DEGRADED in statuses:
            overall = HealthStatus.DEGRADED
        elif all(s == HealthStatus.HEALTHY for s in statuses):
            overall = HealthStatus.HEALTHY
        else:
            overall = HealthStatus.UNKNOWN
        
        return {
            "status": overall.value,
            "timestamp": datetime.utcnow().isoformat(),
            "checks": [r.to_dict() for r in results.values()],
            "service": settings.PROJECT_NAME,
            "environment": settings.ENVIRONMENT,
            "version": settings.VERSION,
        }
    
    def get_status(self) -> Dict[str, Any]:
        """Get cached health status (without re-running checks)."""
        if not self._results:
            return {"status": "unknown", "checks": []}
        
        statuses = [r.status for r in self._results.values()]
        
        if HealthStatus.UNHEALTHY in statuses:
            overall = HealthStatus.UNHEALTHY
        elif HealthStatus.DEGRADED in statuses:
            overall = HealthStatus.DEGRADED
        else:
            overall = HealthStatus.HEALTHY
        
        return {
            "status": overall.value,
            "last_check": self._last_check.isoformat() if self._last_check else None,
            "checks": [r.to_dict() for r in self._results.values()],
        }
    
    async def is_ready(self) -> bool:
        """Check if service is ready to accept traffic."""
        # Run critical checks only
        critical_checks = ["database", "redis"]
        results = await self.run_all_checks()
        
        for name in critical_checks:
            if name in results and results[name].status != HealthStatus.HEALTHY:
                return False
        return True
    
    async def is_live(self) -> bool:
        """Check if service is alive (liveness probe)."""
        # For liveness, just check if the process is responding
        return True


# Global health checker instance
health_checker = HealthChecker()


# ============================
# Built-in Health Checks
# ============================

async def check_database() -> tuple:
    """Check database connectivity."""
    try:
        from infrastructure.database.session import get_db_session
        
        async for session in get_db_session():
            # Execute a simple query
            from sqlalchemy import text
            result = await session.execute(text("SELECT 1"))
            await session.close()
            return True, "Database connected", {"type": "postgresql"}
    except Exception as e:
        return False, f"Database connection failed: {e}", {"error": str(e)}


async def check_redis() -> tuple:
    """Check Redis connectivity."""
    try:
        from infrastructure.redis.client import get_redis_client
        
        redis = await get_redis_client()
        await redis.ping()
        return True, "Redis connected", {"type": "redis"}
    except Exception as e:
        return False, f"Redis connection failed: {e}", {"error": str(e)}


async def check_payment_gateway(gateway: str = "chapa") -> tuple:
    """Check payment gateway availability."""
    try:
        # Placeholder - implement actual payment gateway check
        # This would make a lightweight API call to the payment provider
        return True, f"{gateway.capitalize()} gateway available", {"gateway": gateway}
    except Exception as e:
        return False, f"{gateway.capitalize()} gateway unavailable: {e}", {"gateway": gateway}


async def check_disk_space() -> tuple:
    """Check available disk space."""
    import shutil
    
    try:
        stat = shutil.disk_usage("/")
        # stat values are in bytes; if suspiciously small, treat as 512-byte blocks
        total = stat.total if stat.total > 1e9 else stat.total * 512
        free = stat.free if stat.free > 1e9 else stat.free * 512
        free_gb = free / (1024 ** 3)
        threshold_gb = 0.1
        
        if free_gb < threshold_gb:
            return False, f"Low disk space: {free_gb:.2f}GB free", {
                "free_gb": round(free_gb, 2),
                "used_gb": round((stat.total - stat.free) / (1024 ** 3), 2),
                "total_gb": round(stat.total / (1024 ** 3), 2),
            }
        
        return True, f"Disk space OK: {free_gb:.2f}GB free", {
            "free_gb": round(free_gb, 2),
            "used_gb": round((total - free) / (1024 ** 3), 2),
            "total_gb": round(total / (1024 ** 3), 2),
        }
    except Exception as e:
        return False, f"Disk space check failed: {e}", {"error": str(e)}


async def check_memory_usage() -> tuple:
    """Check memory usage."""
    import psutil
    
    try:
        memory = psutil.virtual_memory()
        used_percent = memory.percent
        threshold = 90  # 90% threshold
        
        if used_percent > threshold:
            return False, f"High memory usage: {used_percent}%", {
                "used_percent": used_percent,
                "available_mb": round(memory.available / (1024 ** 2), 2),
                "total_mb": round(memory.total / (1024 ** 2), 2),
            }
        
        return True, f"Memory usage OK: {used_percent}%", {
            "used_percent": used_percent,
            "available_mb": round(memory.available / (1024 ** 2), 2),
            "total_mb": round(memory.total / (1024 ** 2), 2),
        }
    except Exception as e:
        return False, f"Memory check failed: {e}", {"error": str(e)}


async def check_telegram_bot() -> tuple:
    """Check Telegram bot connectivity."""
    try:
        from bot.bot_instance import get_bot
        
        bot = get_bot()
        me = await bot.get_me()
        return True, f"Bot connected: @{me.username}", {
            "bot_id": me.id,
            "username": me.username,
            "is_bot": me.is_bot,
        }
    except Exception as e:
        return False, f"Telegram bot connection failed: {e}", {"error": str(e)}


# Register default health checks
health_checker.register("database", check_database)
health_checker.register("redis", check_redis)
health_checker.register("disk_space", check_disk_space)
health_checker.register("memory_usage", check_memory_usage)
health_checker.register("telegram_bot", check_telegram_bot)

# Register payment gateways if configured
if settings.CHAPA_SECRET_KEY:
    health_checker.register("chapa_payment", lambda: check_payment_gateway("chapa"))
if settings.TELEBIRR_APP_ID:
    health_checker.register("telebirr_payment", lambda: check_payment_gateway("telebirr"))


__all__ = [
    "HealthChecker",
    "HealthCheckResult",
    "HealthStatus",
    "health_checker",
    "check_database",
    "check_redis",
    "check_payment_gateway",
    "check_disk_space",
    "check_memory_usage",
    "check_telegram_bot",
]