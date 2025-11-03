"""
Base Stage - Parent class for all pipeline stages
"""

from abc import ABC, abstractmethod
from typing import Dict, Any
from datetime import datetime
from marketpilot.utils.logger import log_event


class BaseStage(ABC):
    """Base class for all pipeline stages"""

    def __init__(self, stage_name: str):
        """
        Initialize stage

        Args:
            stage_name: Name of the stage (e.g., 'health_check', 'data_collection')
        """
        self.stage_name = stage_name
        self.start_time = None
        self.end_time = None

    async def execute(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute stage with timing and logging

        Args:
            data: Dictionary containing all pipeline data

        Returns:
            Updated data dictionary
        """
        self.start_time = datetime.now()

        log_event(
            stage=self.stage_name,
            block="stage_execution",
            level="INFO",
            msg=f"Starting {self.stage_name}",
        )

        try:
            # Execute the actual stage logic
            result = await self._process(data)

            self.end_time = datetime.now()
            duration = (self.end_time - self.start_time).total_seconds()

            log_event(
                stage=self.stage_name,
                block="stage_execution",
                level="INFO",
                msg=f"Completed {self.stage_name}",
                extra={
                    "duration_seconds": duration,
                    "status": "success",
                },
            )

            return result

        except Exception as e:
            self.end_time = datetime.now()
            duration = (self.end_time - self.start_time).total_seconds()

            log_event(
                stage=self.stage_name,
                block="stage_execution",
                level="ERROR",
                msg=f"Failed {self.stage_name}: {str(e)}",
                extra={
                    "duration_seconds": duration,
                    "error": str(e),
                },
            )

            raise

    @abstractmethod
    async def _process(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute the core logic of this stage

        Args:
            data: Pipeline data

        Returns:
            Updated data dictionary
        """
        pass