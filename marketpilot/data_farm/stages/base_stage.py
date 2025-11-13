"""
Base Stage - Parent class for all pipeline stages
"""

from abc import ABC, abstractmethod
from typing import Dict, Any
from datetime import datetime
import uuid
from marketpilot.utils.logger import log_event


class BaseStage(ABC):
    """Base class for all pipeline stages with enhanced logging"""

    def __init__(self, stage_name: str):
        """
        Initialize stage

        Args:
            stage_name: Name of the stage (e.g., 'health_check', 'data_collection')
        """
        self.stage_name = stage_name
        self.start_time = None
        self.end_time = None
        self.operation_id = None

    async def execute(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute stage with enhanced timing and logging

        Args:
            data: Dictionary containing all pipeline data

        Returns:
            Updated data dictionary
        """
        # Generate unique operation ID
        self.operation_id = str(uuid.uuid4())[:8]
        self.start_time = datetime.now()

        # Log stage start with operation_id
        log_event(
            stage=self.stage_name,
            block="stage",
            level="INFO",
            msg=f"Starting {self.stage_name}",
            extra={
                "operation_id": self.operation_id,
                "timestamp": self.start_time.isoformat(),
            },
        )

        try:
            # Execute the actual stage logic
            result = await self._process(data)

            self.end_time = datetime.now()
            duration_ms = (self.end_time - self.start_time).total_seconds() * 1000

            # Count records processed
            records_processed = self._count_records(result)

            # Log stage completion with metrics
            log_event(
                stage=self.stage_name,
                block="stage",
                level="INFO",
                msg=f"Completed {self.stage_name}",
                extra={
                    "operation_id": self.operation_id,
                    "duration_ms": round(duration_ms, 2),
                    "records_processed": records_processed,
                    "success_flag": True,
                    "timestamp": self.end_time.isoformat(),
                },
            )

            return result

        except Exception as e:
            self.end_time = datetime.now()
            duration_ms = (self.end_time - self.start_time).total_seconds() * 1000

            # Log stage failure with error details
            log_event(
                stage=self.stage_name,
                block="stage",
                level="ERROR",
                msg=f"Failed {self.stage_name}: {str(e)}",
                extra={
                    "operation_id": self.operation_id,
                    "duration_ms": round(duration_ms, 2),
                    "success_flag": False,
                    "error_type": type(e).__name__,
                    "error_message": str(e),
                    "timestamp": self.end_time.isoformat(),
                },
            )

            raise

    def _count_records(self, data: Dict[str, Any]) -> int:
        """
        Count records processed by this stage

        Args:
            data: Pipeline data

        Returns:
            Number of records processed
        """
        # Try common data keys
        data_keys = [
            "raw_data",
            "processed_data",
            "aligned_data",
            "unique_data",
            "validated_data",
        ]

        for key in data_keys:
            if key in data and isinstance(data[key], list):
                return len(data[key])

        return 0

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
