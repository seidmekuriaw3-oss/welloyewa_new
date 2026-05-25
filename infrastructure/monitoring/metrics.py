from typing import Dict, Any

async def get_metrics() -> Dict[str, Any]:
    return {"status": "ok", "metrics": {}}

__all__ = ["get_metrics"]
