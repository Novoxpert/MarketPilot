"""
Temporal Alignment Stage - Normalize timestamps to UTC ISO format
"""

from typing import Dict, Any
from datetime import datetime
from marketpilot.data_farm.stages.base_stage import BaseStage
from marketpilot.utils.logger import log_event


class TemporalAlignmentStage(BaseStage):
    """Align timestamps to standard UTC ISO format"""

    def __init__(self):
        super().__init__("temporal_alignment")

    async def _process(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize all timestamps to UTC ISO format"""
        processed_data = data.get("processed_data", [])

        aligned_count = 0
        aligned_records = []

        for record in processed_data:
            record_data = record.get("data", {})
            
            # Find and normalize timestamp
            if self._normalize_timestamp(record_data):
                aligned_count += 1

            aligned_records.append(record)

        alignment_rate = (
            f"{(aligned_count/len(processed_data)*100):.1f}%"
            if processed_data
            else "0%"
        )

        log_event(
            stage=self.stage_name,
            block="temporal_alignment",
            level="INFO",
            msg=f"Aligned {aligned_count}/{len(processed_data)} timestamps ({alignment_rate})",
            extra={"aligned_count": aligned_count, "total": len(processed_data)},
        )

        data["aligned_data"] = aligned_records
        data["alignment_stats"] = {
            "aligned_count": aligned_count,
            "total_records": len(processed_data),
            "alignment_rate": alignment_rate,
        }
        return data

    def _normalize_timestamp(self, record_data: Dict[str, Any]) -> bool:
        """
        Find timestamp field and normalize to UTC ISO format
        
        Returns: True if timestamp was found and normalized
        """
        # Try common timestamp field names
        timestamp_fields = [
            "candle_time",
            "timestamp",
            "published_at_utc",
            "date_utc",
            "date",
        ]
        
        for field in timestamp_fields:
            if field not in record_data or not record_data[field]:
                continue
            
            try:
                timestamp = record_data[field]
                
                # Parse to datetime
                if isinstance(timestamp, str):
                    dt = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
                elif isinstance(timestamp, datetime):
                    dt = timestamp
                else:
                    dt = datetime.fromisoformat(str(timestamp))
                
                # Store normalized timestamp
                record_data["timestamp"] = dt.isoformat()
                
                # Also update original field if it's a common one
                if field in ["candle_time", "published_at_utc", "date_utc"]:
                    record_data[field] = dt.isoformat()
                
                return True
                
            except (ValueError, AttributeError):
                continue
        
        return False