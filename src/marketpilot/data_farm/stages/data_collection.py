"""
Data Collection Stage (IMPROVED - Schema-Aware)
"""

from typing import Dict, Any, List, Optional
from datetime import datetime
import asyncio
from marketpilot.data_farm.stages.base_stage import BaseStage
from marketpilot.utils.logger import log_event


class DataCollectionStage(BaseStage):
    """Fetch data from adapters with time range support and schema awareness"""

    def __init__(self):
        super().__init__("data_collection")

    async def _process(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Main data collection process with time range
        """
        adapters = data.get("adapters", [])
        symbols = data.get("symbols", [])
        config = data.get("config", {})
        
        # Extract time range from data (if provided)
        start_date = data.get("start_date")
        end_date = data.get("end_date")
        
        if not adapters:
            log_event(
                stage=self.stage_name,
                block="data_collection",
                level="ERROR",
                msg="No adapters available",
            )
            data["raw_data"] = []
            data["collection_summary"] = {
                "total_fetches": 0,
                "successful": 0,
                "failed": 0,
            }
            return data
        
        if not symbols:
            log_event(
                stage=self.stage_name,
                block="data_collection",
                level="WARNING",
                msg="No symbols to fetch",
            )
            data["raw_data"] = []
            data["collection_summary"] = {
                "total_fetches": 0,
                "successful": 0,
                "failed": 0,
            }
            return data
        
        # Fetch data from all adapters
        fetch_results = await self._fetch_from_adapters(
            adapters, 
            symbols, 
            config,
            start=start_date,
            end=end_date
        )
        
        # Organize into standard format
        organized_records = self._organize_records(fetch_results)
        
        log_event(
            stage=self.stage_name,
            block="data_collection",
            level="INFO",
            msg=f"Collected {len(organized_records)} records",
            extra={
                "total_records": len(organized_records),
                "successful": fetch_results["summary"]["successful"],
                "failed": fetch_results["summary"]["failed"],
                "by_type": self._count_by_type(organized_records),
                "time_range": {
                    "start": start_date.isoformat() if start_date else None,
                    "end": end_date.isoformat() if end_date else None,
                }
            },
        )
        
        data["raw_data"] = organized_records
        data["collection_summary"] = fetch_results["summary"]
        data["collection_errors"] = fetch_results["errors"]
        return data

    async def _fetch_from_adapters(
        self, 
        adapters: List, 
        symbols: List[str],
        config: Dict[str, Any],
        start: Optional[datetime] = None,
        end: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        """
        Fetch data from all adapters with optional time range
        """
        results = {
            "by_type": {"price": {}, "news": {}, "fundamental": {}},
            "summary": {
                "total_fetches": 0,
                "successful": 0,
                "failed": 0,
                "total_records": 0,
            },
            "errors": [],
        }
        
        # Group adapters by type
        adapters_by_type = {}
        for adapter in adapters:
            adapter_type = getattr(adapter, "schema_type", "unknown")
            if adapter_type not in adapters_by_type:
                adapters_by_type[adapter_type] = []
            adapters_by_type[adapter_type].append(adapter)
        
        # Fetch for each data type
        for data_type, type_adapters in adapters_by_type.items():
            if not type_adapters:
                continue
            
            adapter = type_adapters[0]
            
            log_event(
                stage=self.stage_name,
                block="fetch",
                level="INFO",
                msg=f"Fetching {data_type} data using {adapter.adapter_id}",
                extra={
                    "data_type": data_type,
                    "adapter_id": adapter.adapter_id,
                    "symbols": len(symbols),
                    "time_range": {
                        "start": start.isoformat() if start else None,
                        "end": end.isoformat() if end else None,
                    }
                },
            )
            
            # Pass start/end to each fetch
            tasks = [
                self._fetch_single(
                    adapter, 
                    symbol, 
                    data_type, 
                    results,
                    start=start,
                    end=end
                )
                for symbol in symbols
            ]
            await asyncio.gather(*tasks, return_exceptions=True)
        
        return results

    async def _fetch_single(
        self,
        adapter,
        symbol: str,
        data_type: str,
        results: Dict[str, Any],
        start: Optional[datetime] = None,
        end: Optional[datetime] = None,
    ):
        """Fetch data for a single symbol with time range"""
        results["summary"]["total_fetches"] += 1
        
        try:
            # Pass start/end to adapter
            fetch_result = await adapter.execute_ingest(
                symbol,
                start=start,
                end=end
            )
            
            if fetch_result.get("success"):
                data = fetch_result.get("data")
                
                results["by_type"][data_type][symbol] = {
                    "data": data,
                    "adapter_id": adapter.adapter_id,
                    "vendor": adapter.vendor,
                    "ingested_at": fetch_result.get("ingested_at"),
                    "record_count": fetch_result.get("record_count", 0),
                }
                
                results["summary"]["successful"] += 1
                results["summary"]["total_records"] += fetch_result.get("record_count", 0)
                
                log_event(
                    stage=self.stage_name,
                    block="fetch",
                    level="DEBUG",
                    msg=f"Fetched {data_type} for {symbol}",
                    extra={
                        "symbol": symbol,
                        "data_type": data_type,
                        "records": fetch_result.get("record_count", 0),
                    },
                )
            else:
                error_msg = fetch_result.get("error", "Unknown error")
                results["summary"]["failed"] += 1
                results["errors"].append({
                    "symbol": symbol,
                    "data_type": data_type,
                    "adapter_id": adapter.adapter_id,
                    "error": error_msg,
                })
                
                results["by_type"][data_type][symbol] = {
                    "data": None,
                    "adapter_id": adapter.adapter_id,
                    "vendor": adapter.vendor,
                    "error": error_msg,
                }
                
                log_event(
                    stage=self.stage_name,
                    block="fetch",
                    level="WARNING",
                    msg=f"Failed to fetch {data_type} for {symbol}",
                    extra={"symbol": symbol, "error": error_msg},
                )
        
        except Exception as e:
            results["summary"]["failed"] += 1
            results["errors"].append({
                "symbol": symbol,
                "data_type": data_type,
                "adapter_id": adapter.adapter_id,
                "error": str(e),
            })
            
            results["by_type"][data_type][symbol] = {
                "data": None,
                "adapter_id": adapter.adapter_id,
                "vendor": adapter.vendor,
                "error": str(e),
            }
            
            log_event(
                stage=self.stage_name,
                block="fetch",
                level="ERROR",
                msg=f"Exception fetching {data_type} for {symbol}: {str(e)}",
            )

    def _organize_records(self, fetch_results: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Organize fetched data into standard record format
        
        SCHEMA-AWARE: Handles different data structures:
        - Price: List of flat records
        - News: Wrapper with data array
        - Fundamental: Wrapper with data object
        """
        organized = []
        
        for data_type, symbols_data in fetch_results["by_type"].items():
            for symbol, fetch_data in symbols_data.items():
                if fetch_data.get("data") is None:
                    continue
                
                # Extract individual records based on schema type
                records = self._extract_records(
                    fetch_data["data"], 
                    data_type
                )
                
                # Create organized records
                for record in records:
                    organized.append({
                        "adapter_id": fetch_data["adapter_id"],
                        "symbol": symbol,
                        "vendor": fetch_data["vendor"],
                        "schema_type": data_type,
                        "data": record,
                        "ingested_at": fetch_data.get("ingested_at", ""),
                    })
        
        return organized

    def _extract_records(self, data: Any, data_type: str) -> List[Dict]:
        """
        Extract individual records from fetched data (SCHEMA-AWARE)
        
        Schema formats:
        - price: List[Dict] - flat records
        - news: Dict with 'data' array
        - fundamental: Dict with 'data' object (single record)
        
        Args:
            data: Raw data from adapter
            data_type: Schema type (price, news, fundamental)
        
        Returns:
            List of individual records
        """
        # Price: Already a list of flat records
        if data_type == "price":
            if isinstance(data, list):
                return data
            else:
                log_event(
                    stage=self.stage_name,
                    block="extract_records",
                    level="WARNING",
                    msg=f"Expected list for price data, got {type(data)}",
                )
                return []
        
        # News: Wrapper with data array
        elif data_type == "news":
            if isinstance(data, dict) and "data" in data:
                news_items = data["data"]
                if isinstance(news_items, list):
                    return news_items
                else:
                    log_event(
                        stage=self.stage_name,
                        block="extract_records",
                        level="WARNING",
                        msg=f"Expected list in news.data, got {type(news_items)}",
                    )
                    return []
            elif isinstance(data, list):
                # Fallback: already unwrapped
                return data
            else:
                log_event(
                    stage=self.stage_name,
                    block="extract_records",
                    level="WARNING",
                    msg=f"Unexpected news data structure: {type(data)}",
                )
                return []
        
        # Fundamental: Wrapper with data object (single record)
        elif data_type == "fundamental":
            if isinstance(data, dict):
                if "data" in data:
                    # Return as single-item list
                    return [data["data"]]
                else:
                    # Already unwrapped, return as single-item list
                    return [data]
            else:
                log_event(
                    stage=self.stage_name,
                    block="extract_records",
                    level="WARNING",
                    msg=f"Expected dict for fundamental data, got {type(data)}",
                )
                return []
        
        # Unknown type: try generic extraction
        else:
            log_event(
                stage=self.stage_name,
                block="extract_records",
                level="WARNING",
                msg=f"Unknown data type: {data_type}, using generic extraction",
            )
            
            if isinstance(data, list):
                return data
            elif isinstance(data, dict):
                if "data" in data:
                    nested = data["data"]
                    if isinstance(nested, list):
                        return nested
                    else:
                        return [nested]
                else:
                    return [data]
            else:
                return []

    def _count_by_type(self, records: List[Dict]) -> Dict[str, int]:
        """Count records by schema type"""
        counts = {}
        for record in records:
            schema_type = record.get("schema_type", "unknown")
            counts[schema_type] = counts.get(schema_type, 0) + 1
        return counts