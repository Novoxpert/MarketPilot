"""
Data Collection Stage - Run all adapters and collect data
"""

from typing import Dict, Any
from marketpilot.data_farm.stages.base_stage import BaseStage
from marketpilot.utils.logger import log_event


class DataCollectionStage(BaseStage):
    """Collect data from all adapters"""

    def __init__(self):
        super().__init__("data_collection")

    async def _process(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Execute all adapters and collect data"""
        adapters = data.get("adapters", [])
        symbols = data.get("symbols", [])

        collected_records = []

        for adapter in adapters:
            for symbol in symbols:
                try:
                    result = await adapter.execute_ingest(symbol)

                    if result.get("success"):
                        collected_records.append(
                            {
                                "adapter_id": adapter.adapter_id,
                                "symbol": symbol,
                                "vendor": result.get("vendor"),
                                "data": result.get("data"),
                                "ingested_at": result.get("ingested_at"),
                            }
                        )
                except Exception as e:
                    log_event(
                        stage=self.stage_name,
                        block="data_collection",
                        level="ERROR",
                        msg=f"Failed to collect from {adapter.adapter_id} for {symbol}",
                        extra={"error": str(e)},
                    )

        log_event(
            stage=self.stage_name,
            block="data_collection",
            level="INFO",
            msg=f"Collected {len(collected_records)} records",
            extra={"total_records": len(collected_records)},
        )

        data["raw_data"] = collected_records
        return data