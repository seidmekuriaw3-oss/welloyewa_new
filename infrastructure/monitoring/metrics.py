<<<<<<< HEAD
from typing import Dict, Any

async def get_metrics() -> Dict[str, Any]:
    return {"status": "ok", "metrics": {}}

__all__ = ["get_metrics"]
=======
from core.monitoring.metrics import get_metrics, setup_metrics
__all__ = ["get_metrics", "setup_metrics"]
>>>>>>> 58a16d4ee3078d96a16a22860de294107e7c3aef
