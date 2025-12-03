"""
Temporal Alignment Stage - Normalize timestamps to Unix milliseconds
"""

from typing import Dict, Any
from datetime import datetime, timezone
from marketpilot.utils.logger import log_event
from marketpilot.data_farm.stages.base_stage import BaseStage


class TemporalAlignmentStage(BaseStage):
    """Align timestamps to Unix milliseconds format"""

    def __init__(self):
        super().__init__("temporal_alignment")

    async def _process(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize all timestamps to Unix milliseconds (int)"""
        processed_data = data.get("processed_data", [])

        aligned_count = 0
        failed_count = 0
        aligned_records = []

        for record in processed_data:
            record_data = record.get("data", {})
            
            # Find and normalize timestamp
            result = self._normalize_timestamp(record_data)
            if result:
                aligned_count += 1
            else:
                failed_count += 1

            aligned_records.append(record)

        alignment_rate = (
            f"{(aligned_count/len(processed_data)*100):.1f}%"
            if processed_data
            else "0%"
        )

        log_event(
            stage=self.stage_name,
            block="temporal_alignment",
            level="INFO" if failed_count == 0 else "WARNING",
            msg=f"Aligned {aligned_count}/{len(processed_data)} timestamps ({alignment_rate})",
            extra={
                "aligned_count": aligned_count,
                "failed_count": failed_count,
                "total": len(processed_data)
            },
        )

        data["aligned_data"] = aligned_records
        data["alignment_stats"] = {
            "aligned_count": aligned_count,
            "failed_count": failed_count,
            "total_records": len(processed_data),
            "alignment_rate": alignment_rate,
        }
        return data

    def _normalize_timestamp(self, record_data: Dict[str, Any]) -> bool:
        """
        Find timestamp field and normalize to Unix milliseconds (int)
        
        Supported formats:
        - ISO string: "2025-11-30T22:14:00" or "2025-11-30T22:14:00Z"
        - Unix seconds: 1764540840 (int/float)
        - Unix milliseconds: 1764540840000 (int)
        - datetime object
        
        Returns: True if timestamp was normalized successfully
        """
        # Timestamp field priority order
        timestamp_fields = [
            "candle_time",      # Price data
            "timestamp",        # Generic
            "releasedAt",       # News data
            "date_utc",         # Fundamental data
            "date",             # Generic date
        ]
        
        for field in timestamp_fields:
            if field not in record_data or record_data[field] is None:
                continue
            
            try:
                raw_value = record_data[field]
                unix_ms = self._convert_to_unix_ms(raw_value)
                
                if unix_ms is not None:
                    # Store Unix ms in standard 'timestamp' field
                    record_data["timestamp"] = unix_ms
                                   
                    return True
                    
            except Exception as e:
                log_event(
                    stage=self.stage_name,
                    block="normalize_timestamp",
                    level="WARNING",
                    msg=f"Failed to parse timestamp field '{field}': {str(e)}",
                    extra={
                        "field": field,
                        "value": str(raw_value)[:100],
                        "error": str(e)
                    },
                )
                continue
        
        log_event(
            stage=self.stage_name,
            block="normalize_timestamp",
            level="WARNING",
            msg="No valid timestamp field found",
            extra={"available_fields": list(record_data.keys())},
        )
        return False

    def _convert_to_unix_ms(self, value: Any) -> int:
        """
        Convert various timestamp formats to Unix milliseconds (int)
        
        Args:
            value: Timestamp in various formats
            
        Returns:
            Unix timestamp in milliseconds (int) or None if conversion fails
        """
        # Case 1: Already Unix timestamp (int or float)
        if isinstance(value, (int, float)):
            # Determine if seconds or milliseconds
            # Heuristic: If value > 10^10, it's milliseconds
            # Year 2286 in seconds = 10^10
            if value > 10_000_000_000:
                # Already milliseconds
                return int(value)
            else:
                # Seconds - convert to milliseconds
                return int(value * 1000)
        
        # Case 2: ISO string format
        elif isinstance(value, str):
            # Clean up string (remove 'Z' suffix)
            cleaned = value.replace("Z", "+00:00").strip()
            
            # Parse to datetime
            try:
                dt = datetime.fromisoformat(cleaned)
            except ValueError:
                # Try alternative formats
                for fmt in [
                    "%Y-%m-%dT%H:%M:%S",
                    "%Y-%m-%d %H:%M:%S",
                    "%Y-%m-%d",
                ]:
                    try:
                        dt = datetime.strptime(cleaned, fmt)
                        break
                    except ValueError:
                        continue
                else:
                    return None
            
            # Ensure UTC timezone
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            
            # Convert to Unix milliseconds
            return int(dt.timestamp() * 1000)
        
        # Case 3: datetime object
        elif isinstance(value, datetime):
            # Ensure UTC timezone
            if value.tzinfo is None:
                value = value.replace(tzinfo=timezone.utc)
            
            # Convert to Unix milliseconds
            return int(value.timestamp() * 1000)
        
        # Unknown type
        else:
            log_event(
                stage=self.stage_name,
                block="convert_to_unix_ms",
                level="WARNING",
                msg=f"Unsupported timestamp type: {type(value)}",
                extra={"value_type": str(type(value)), "value": str(value)[:50]},
            )
            return None