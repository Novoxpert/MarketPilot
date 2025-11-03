"""
Temporal Alignment Stage - Align timestamps across data sources
"""

from typing import Dict, Any
from datetime import datetime
from marketpilot.data_farm.stages.base_stage import BaseStage
from marketpilot.utils.logger import log_event


class TemporalAlignmentStage(BaseStage):
    """Align temporal data across different sources"""

    def __init__(self):
        super().__init__("temporal_alignment")

    async def _process(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Align timestamps in processed data"""
        processed_data = data.get("processed_data", [])

        aligned_count = 0
        aligned_records = []

        for record in processed_data:
            record_data = record.get("data", {})

            # Normalize timestamp if present
            timestamp = record_data.get("timestamp")
            if timestamp:
                try:
                    # Ensure ISO format
                    if isinstance(timestamp, str):
                        dt = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
                    else:
                        dt = timestamp

                    record_data["timestamp"] = dt.isoformat()
                    record_data["timestamp_aligned"] = True
                    aligned_count += 1

                except Exception as e:
                    log_event(
                        stage=self.stage_name,
                        block="temporal_alignment",
                        level="WARNING",
                        msg=f"Failed to align timestamp: {str(e)}",
                        extra={
                            "symbol": record.get("symbol"),
                            "timestamp": str(timestamp),
                        },
                    )
                    record_data["timestamp_aligned"] = False

            aligned_records.append(record)

        log_event(
            stage=self.stage_name,
            block="temporal_alignment",
            level="INFO",
            msg=f"Aligned {aligned_count} timestamps",
            extra={"aligned_count": aligned_count},
        )

        data["aligned_data"] = aligned_records
        data["alignment_stats"] = {"aligned_count": aligned_count}
        return data