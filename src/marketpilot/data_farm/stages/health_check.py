"""
Health Check Stage - Validate adapters are loaded
"""

from typing import Dict, Any
from marketpilot.data_farm.stages.base_stage import BaseStage
from marketpilot.utils.logger import log_event


class HealthCheckStage(BaseStage):
    """Check that adapters are initialized and ready"""

    def __init__(self):
        super().__init__("health_check")

    async def _process(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Verify adapters are loaded
        
        Simple check: if adapters list exists and has items, we're healthy
        """
        adapters = data.get("adapters", [])
        
        health_status = {
            "total_adapters": len(adapters),
            "status": "healthy" if adapters else "no_adapters",
        }
        
        log_event(
            stage=self.stage_name,
            block="health_check",
            level="INFO" if adapters else "WARNING",
            msg=f"Health check: {len(adapters)} adapters loaded",
            extra=health_status,
        )
        
        data["health_check"] = health_status
        return data