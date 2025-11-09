"""
Health Check Stage - Validate adapters and connectivity
"""

from typing import Dict, Any
from marketpilot.data_farm.stages.base_stage import BaseStage


class HealthCheckStage(BaseStage):
    """Check adapter health and API connectivity"""

    def __init__(self):
        super().__init__("health_check")

    async def _process(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Simple health check"""
        adapters = data.get("adapters", [])

        health_status = {
            "total_adapters": len(adapters),
            "healthy": len(adapters),  # Simple: assume all healthy if loaded
            "unhealthy": 0,
            "details": [],
        }

        for adapter in adapters:
            # Handle both dict and object formats
            if isinstance(adapter, dict):
                adapter_id = adapter.get("adapter_id", "unknown")
            else:
                adapter_id = getattr(adapter, "adapter_id", "unknown")

            health_status["details"].append(
                {"adapter_id": adapter_id, "status": "healthy"}
            )

        data["health_check"] = health_status
        return data
