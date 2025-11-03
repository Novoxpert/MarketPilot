"""
NaN Processing Stage - Handle missing values
"""

from typing import Dict, Any
import math
from marketpilot.data_farm.stages.base_stage import BaseStage
from marketpilot.utils.logger import log_event


class NaNProcessingStage(BaseStage):
    """Process and handle NaN/missing values"""

    def __init__(self):
        super().__init__("nan_processing")

    async def _process(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Process NaN values in raw data"""
        raw_data = data.get("raw_data", [])

        nan_count = 0
        processed_records = []

        for record in raw_data:
            record_data = record.get("data", {})

            # Check each field for NaN/None
            for key, value in record_data.items():
                if value is None or (isinstance(value, float) and math.isnan(value)):
                    nan_count += 1
                    # Simple strategy: replace with 0
                    record_data[key] = 0
                    log_event(
                        stage=self.stage_name,
                        block="nan_processing",
                        level="DEBUG",
                        msg=f"NaN replaced in field: {key}",
                        extra={
                            "symbol": record.get("symbol"),
                            "adapter_id": record.get("adapter_id"),
                        },
                    )

            processed_records.append(record)

        log_event(
            stage=self.stage_name,
            block="nan_processing",
            level="INFO",
            msg=f"Processed {nan_count} NaN values",
            extra={"nan_count": nan_count},
        )

        data["processed_data"] = processed_records
        data["nan_stats"] = {"nan_count": nan_count}
        return data