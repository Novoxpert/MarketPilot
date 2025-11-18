"""
Deduplication Stage - Remove duplicate records
"""

from typing import Dict, Any, Set
from marketpilot.data_farm.stages.base_stage import BaseStage
from marketpilot.utils.logger import log_event


class DeduplicationStage(BaseStage):
    """Remove duplicate records from data"""

    def __init__(self):
        super().__init__("deduplication")

    async def _process(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Remove duplicate records"""
        aligned_data = data.get("aligned_data", [])

        unique_records = []
        seen_keys: Set[str] = set()
        duplicates_removed = 0

        for record in aligned_data:
            record_data = record.get("data", {})

            # Get timestamp from multiple possible fields
            timestamp_value = (
                record_data.get("timestamp")
                or record_data.get("candle_time")
                or record_data.get("published_at_utc")
                or record_data.get("date_utc")
                or "no_timestamp"
            )

            # Create unique key based on data type
            schema_type = record.get("schema_type", "unknown")

            if schema_type == "price":
                # For price: symbol + candle_time
                unique_key = f"{record.get('symbol')}_{timestamp_value}"
            elif schema_type == "news":
                # For news: news_id + symbol (if available)
                news_id = record_data.get("news_id", record_data.get("id", "no_id"))
                unique_key = f"{record.get('symbol')}_{news_id}"
            elif schema_type == "fundamental":
                # For fundamental: symbol + metric + date
                metric = record_data.get("metric", "unknown_metric")
                unique_key = f"{record.get('symbol')}_{metric}_{timestamp_value}"
            else:
                # Generic: adapter_id + symbol + timestamp
                unique_key = (
                    f"{record.get('adapter_id')}_"
                    f"{record.get('symbol')}_"
                    f"{timestamp_value}"
                )

            if unique_key in seen_keys:
                duplicates_removed += 1
                log_event(
                    stage=self.stage_name,
                    block="deduplication",
                    level="DEBUG",
                    msg="Duplicate removed",
                    extra={
                        "symbol": record.get("symbol"),
                        "adapter_id": record.get("adapter_id"),
                        "schema_type": schema_type,
                        "unique_key": unique_key,
                    },
                )
            else:
                seen_keys.add(unique_key)
                unique_records.append(record)

        dedup_rate = (
            f"{(len(unique_records)/len(aligned_data)*100):.1f}%"
            if aligned_data
            else "0%"
        )

        log_event(
            stage=self.stage_name,
            block="deduplication",
            level="INFO",
            msg=f"Removed {duplicates_removed} duplicates, kept {len(unique_records)} unique records",
            extra={
                "duplicates_removed": duplicates_removed,
                "unique_records": len(unique_records),
                "original_records": len(aligned_data),
                "deduplication_rate": dedup_rate,
            },
        )

        data["unique_data"] = unique_records
        data["dedup_stats"] = {
            "duplicates_removed": duplicates_removed,
            "unique_records": len(unique_records),
            "original_records": len(aligned_data),
            "deduplication_rate": dedup_rate,
        }
        return data
