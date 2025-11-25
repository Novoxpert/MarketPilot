"""
Deduplication Stage - Remove duplicate records
"""

from typing import Dict, Any, Set
from marketpilot.data_farm.stages.base_stage import BaseStage
from marketpilot.utils.logger import log_event


class DeduplicationStage(BaseStage):
    """Remove duplicate records based on unique keys"""

    def __init__(self):
        super().__init__("deduplication")

    async def _process(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Remove duplicates using type-specific unique keys"""
        aligned_data = data.get("aligned_data", [])

        unique_records = []
        seen_keys: Set[str] = set()
        duplicates_removed = 0

        for record in aligned_data:
            # Generate unique key based on data type
            unique_key = self._generate_unique_key(record)
            
            if unique_key in seen_keys:
                duplicates_removed += 1
            else:
                seen_keys.add(unique_key)
                unique_records.append(record)

        log_event(
            stage=self.stage_name,
            block="deduplication",
            level="INFO",
            msg=f"Removed {duplicates_removed} duplicates, kept {len(unique_records)} unique",
            extra={
                "duplicates_removed": duplicates_removed,
                "unique_records": len(unique_records),
                "original_records": len(aligned_data),
            },
        )

        data["unique_data"] = unique_records
        data["dedup_stats"] = {
            "duplicates_removed": duplicates_removed,
            "unique_records": len(unique_records),
            "original_records": len(aligned_data),
        }
        return data

    def _generate_unique_key(self, record: Dict[str, Any]) -> str:
        """
        Generate unique key for deduplication
        
        Rules:
        - price: symbol + timestamp
        - news: symbol + news_id
        - fundamental: symbol + metric + timestamp
        - default: adapter_id + symbol + timestamp
        """
        symbol = record.get("symbol", "no_symbol")
        schema_type = record.get("schema_type", "unknown")
        record_data = record.get("data", {})
        
        # Get timestamp
        timestamp = (
            record_data.get("timestamp")
            or record_data.get("candle_time")
            or record_data.get("published_at_utc")
            or record_data.get("date_utc")
            or "no_timestamp"
        )
        
        # Type-specific keys
        if schema_type == "price":
            return f"price:{symbol}:{timestamp}"
        
        elif schema_type == "news":
            news_id = record_data.get("news_id") or record_data.get("slug") or "no_id"
            return f"news:{symbol}:{news_id}"
        
        elif schema_type == "fundamental":
            metric = record_data.get("metric", "no_metric")
            return f"fundamental:{symbol}:{metric}:{timestamp}"
        
        else:
            adapter_id = record.get("adapter_id", "no_adapter")
            return f"{schema_type}:{adapter_id}:{symbol}:{timestamp}"