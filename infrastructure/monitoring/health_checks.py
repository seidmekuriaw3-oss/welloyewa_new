from typing import Dict, Any

class HealthChecker:
    async def check_all(self) -> Dict[str, Any]:
        return {"status": "healthy"}

health_checker = HealthChecker()

__all__ = ["HealthChecker", "health_checker"]
