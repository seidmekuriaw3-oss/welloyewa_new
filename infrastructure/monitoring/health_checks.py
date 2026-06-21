<<<<<<< HEAD
from typing import Dict, Any

class HealthChecker:
    async def check_all(self) -> Dict[str, Any]:
        return {"status": "healthy"}

health_checker = HealthChecker()

__all__ = ["HealthChecker", "health_checker"]
=======
from core.monitoring.health_checks import health_checker
__all__ = ["health_checker"]
>>>>>>> 58a16d4ee3078d96a16a22860de294107e7c3aef
