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

            # Try multiple timestamp field names
            timestamp_fields = [
                "candle_time",
                "timestamp",
                "published_at_utc",
                "date_utc",
            ]
            timestamp = None

            for field in timestamp_fields:
                if field in record_data and record_data[field]:
                    timestamp = record_data[field]
                    break

            if timestamp:
                try:
                    # Ensure ISO format
                    if isinstance(timestamp, str):
                        # Handle different formats
                        dt = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
                    elif isinstance(timestamp, datetime):
                        dt = timestamp
                    else:
                        dt = datetime.fromisoformat(str(timestamp))

                    # Normalize to UTC ISO format
                    record_data["timestamp"] = dt.isoformat()

                    # Keep original field as well
                    if "candle_time" in record_data:
                        record_data["candle_time"] = dt.isoformat()

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
                            "error": str(e),
                        },
                    )
                    record_data["timestamp_aligned"] = False
            else:
                log_event(
                    stage=self.stage_name,
                    block="temporal_alignment",
                    level="WARNING",
                    msg="No timestamp field found in record",
                    extra={
                        "symbol": record.get("symbol"),
                        "adapter_id": record.get("adapter_id"),
                        "available_fields": list(record_data.keys()),
                    },
                )
                record_data["timestamp_aligned"] = False

            aligned_records.append(record)

        log_event(
            stage=self.stage_name,
            block="temporal_alignment",
            level="INFO",
            msg=f"Aligned {aligned_count} timestamps out of {len(processed_data)} records",
            extra={
                "aligned_count": aligned_count,
                "total_records": len(processed_data),
            },
        )

        data["aligned_data"] = aligned_records
        data["alignment_stats"] = {
            "aligned_count": aligned_count,
            "total_records": len(processed_data),
            "alignment_rate": (
                f"{(aligned_count/len(processed_data)*100):.1f}%"
                if processed_data
                else "0%"
            ),
        }
        return data
