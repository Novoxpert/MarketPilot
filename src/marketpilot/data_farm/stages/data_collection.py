"""
Data Collection Stage - Organize fetched data into standard format
"""

from typing import Dict, Any, List
from marketpilot.data_farm.stages.base_stage import BaseStage
from marketpilot.utils.logger import log_event


class DataCollectionStage(BaseStage):
    """Convert fetched data into standardized record format"""

    def __init__(self):
        super().__init__("data_collection")

    async def _process(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Organize raw_data into standard record format
        
        Expected input: data["raw_data"] = {
            "price": {symbol: [records]},
            "news": {symbol: {data: [articles]}},
            "fundamental": {symbol: records}
        }
        
        Output: data["raw_data"] = [
            {adapter_id, symbol, vendor, schema_type, data, ingested_at}
        ]
        """
        raw_data_by_type = data.get("raw_data", {})

        if not raw_data_by_type:
            log_event(
                stage=self.stage_name,
                block="data_collection",
                level="WARNING",
                msg="No raw_data found",
            )
            data["raw_data"] = []
            return data

        # Get adapter mapping from config
        config = data.get("config", {})
        adapter_map = self._build_adapter_map(config.get("adapters", []))

        collected = []

        # Process each data type
        for data_type, symbols_data in raw_data_by_type.items():
            adapter_info = adapter_map.get(data_type, {
                "id": f"{data_type}_adapter",
                "vendor": "unknown"
            })
            
            for symbol, symbol_data in symbols_data.items():
                records = self._extract_records(symbol_data, data_type)
                
                for record in records:
                    collected.append({
                        "adapter_id": adapter_info["id"],
                        "symbol": symbol,
                        "vendor": adapter_info["vendor"],
                        "schema_type": data_type,
                        "data": record,
                        "ingested_at": self._extract_timestamp(record, data_type),
                    })

        log_event(
            stage=self.stage_name,
            block="data_collection",
            level="INFO",
            msg=f"Organized {len(collected)} records",
            extra={
                "total_records": len(collected),
                "by_type": self._count_by_type(collected),
            },
        )

        data["raw_data"] = collected
        return data

    def _build_adapter_map(self, adapters_config: List[Dict]) -> Dict[str, Dict]:
        """Build mapping of data_type -> adapter info"""
        return {
            adapter["type"]: {
                "id": adapter.get("id", f"{adapter['type']}_adapter"),
                "vendor": adapter.get("vendor", "unknown"),
            }
            for adapter in adapters_config
            if "type" in adapter
        }

    def _extract_records(self, symbol_data: Any, data_type: str) -> List[Dict]:
        """
        Extract individual records from symbol data
        
        Handles different formats:
        - List of records: [record1, record2, ...]
        - Dict with 'data' field: {data: [records]}
        - Single record: {field: value}
        """
        # List of records (price format)
        if isinstance(symbol_data, list):
            return symbol_data
        
        # Dict with nested 'data' array (news format)
        if isinstance(symbol_data, dict):
            if "data" in symbol_data and isinstance(symbol_data["data"], list):
                return symbol_data["data"]
            # Single record dict
            return [symbol_data]
        
        return []

    def _extract_timestamp(self, record: Dict, data_type: str) -> str:
        """Extract timestamp from record"""
        timestamp_fields = {
            "price": ["candle_time", "timestamp"],
            "news": ["published_at_utc", "releasedAt", "timestamp"],
            "fundamental": ["date_utc", "date", "timestamp"],
        }
        
        fields = timestamp_fields.get(data_type, ["timestamp"])
        
        for field in fields:
            if field in record and record[field]:
                return str(record[field])
        
        return ""

    def _count_by_type(self, records: List[Dict]) -> Dict[str, int]:
        """Count records by schema type"""
        counts = {}
        for record in records:
            schema_type = record.get("schema_type", "unknown")
            counts[schema_type] = counts.get(schema_type, 0) + 1
        return counts