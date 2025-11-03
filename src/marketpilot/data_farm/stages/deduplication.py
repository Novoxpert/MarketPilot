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

            # Create unique key: adapter_id + symbol + timestamp
            unique_key = (
                f"{record.get('adapter_id')}_"
                f"{record.get('symbol')}_"
                f"{record_data.get('timestamp', 'no_timestamp')}"
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
                    },
                )
            else:
                seen_keys.add(unique_key)
                unique_records.append(record)

        log_event(
            stage=self.stage_name,
            block="deduplication",
            level="INFO",
            msg=f"Removed {duplicates_removed} duplicates",
            extra={
                "duplicates_removed": duplicates_removed,
                "unique_records": len(unique_records),
            },
        )

        data["unique_data"] = unique_records
        data["dedup_stats"] = {
            "duplicates_removed": duplicates_removed,
            "unique_records": len(unique_records),
        }
        return data