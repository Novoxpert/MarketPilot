"""
ResilientDataFarm - Main orchestrator for data pipeline
"""

from typing import Dict, Any, List, Optional
from pathlib import Path
from datetime import datetime
import asyncio
from marketpilot.utils.config_loader import load_config
from marketpilot.utils.logger import log_event, setup_logging
from marketpilot.data_farm.adapters.base_adapter import BaseAdapter
from marketpilot.data_farm.adapters.price_adapter import ResilientPriceAdapter
from marketpilot.data_farm.adapters.news_adapter import ResilientNewsAdapter
from marketpilot.data_farm.adapters.fundamental_adapter import ResilientFundamentalAdapter

# Import pipeline stages
from marketpilot.data_farm.stages.health_check import HealthCheckStage
from marketpilot.data_farm.stages.data_collection import DataCollectionStage
from marketpilot.data_farm.stages.nan_processing import NaNProcessingStage
from marketpilot.data_farm.stages.temporal_alignment import TemporalAlignmentStage
from marketpilot.data_farm.stages.deduplication import DeduplicationStage
from marketpilot.data_farm.stages.quality_assurance import QualityAssuranceStage
from marketpilot.data_farm.stages.data_export import DataExportStage

from dotenv import load_dotenv
load_dotenv()   # loads .env automatically

class ResilientDataFarm:
    """Main orchestrator for Data Farm pipeline"""

    def __init__(
        self, config_path: str = "src/marketpilot/configs/data/data_farm_config.yml"
    ):
        """
        Initialize ResilientDataFarm

        Args:
            config_path: Path to main configuration file
        """
        log_event(
            stage="initialization",
            block="data_farm",
            level="INFO",
            msg="Starting ResilientDataFarm initialization",
            extra={"config_path": config_path},
        )

        # Load configuration
        self.config = load_config(config_path)
        self.adapters: Dict[str, BaseAdapter] = {}
        self.adapters_by_type: Dict[str, List[BaseAdapter]] = {
            "price": [],
            "news": [],
            "fundamental": [],
        }

        # Initialize pipeline stages
        self.stages = [
            HealthCheckStage(),
            DataCollectionStage(),
            NaNProcessingStage(),
            TemporalAlignmentStage(),
            DeduplicationStage(),
            QualityAssuranceStage(),
            DataExportStage(),
        ]

        # Initialize components
        self._initialize_components()
        self._initialize_adapters()

        log_event(
            stage="initialization",
            block="data_farm",
            level="INFO",
            msg="ResilientDataFarm initialized",
            extra={
                "adapters": len(self.adapters),
                "stages": len(self.stages),
            },
        )

    def _initialize_components(self):
        """Initialize core components (logging, directories)"""
        # Setup logging
        log_level = self.config.get("logging", {}).get("level", "INFO")
        setup_logging(log_level)

        # Create output directory
        output_dir = self.config.get("output", {}).get("base_dir", "data_farm_exports")
        Path(output_dir).mkdir(parents=True, exist_ok=True)

        log_event(
            stage="initialization",
            block="components",
            level="INFO",
            msg="Components initialized",
            extra={"log_level": log_level, "output_dir": output_dir},
        )

    def _initialize_adapters(self):
        """Initialize all adapters from configuration"""
        adapters_config = self.config.get("adapters", [])

        if not adapters_config:
            log_event(
                stage="initialization",
                block="adapters",
                level="WARNING",
                msg="No adapters defined in configuration",
            )
            return

        # Map adapter types to classes
        adapter_classes = {
            "price": ResilientPriceAdapter,
            "news": ResilientNewsAdapter,
            "fundamental": ResilientFundamentalAdapter,
        }

        # Create adapter instances
        for adapter_config in adapters_config:
            adapter_type = adapter_config.get("type")
            adapter_id = adapter_config.get("id")

            if not adapter_type or adapter_type not in adapter_classes:
                log_event(
                    stage="initialization",
                    block="adapters",
                    level="ERROR",
                    msg=f"Unknown adapter type: {adapter_type}",
                    extra={"adapter_id": adapter_id},
                )
                continue

            try:
                adapter_class = adapter_classes[adapter_type]
                adapter = adapter_class(adapter_config)

                self.adapters[adapter_id] = adapter
                self.adapters_by_type[adapter_type].append(adapter)

                log_event(
                    stage="initialization",
                    block="adapters",
                    level="INFO",
                    msg=f"Loaded adapter: {adapter_id}",
                    extra={"type": adapter_type, "vendor": adapter_config.get("vendor")},
                )

            except Exception as e:
                log_event(
                    stage="initialization",
                    block="adapters",
                    level="ERROR",
                    msg=f"Failed to load adapter: {str(e)}",
                    extra={"adapter_id": adapter_id, "error": str(e)},
                )

        log_event(
            stage="initialization",
            block="adapters",
            level="INFO",
            msg="Adapter initialization complete",
            extra={
                "total": len(self.adapters),
                "price": len(self.adapters_by_type["price"]),
                "news": len(self.adapters_by_type["news"]),
                "fundamental": len(self.adapters_by_type["fundamental"]),
            },
        )

    async def fetch_data_for_symbols(
        self, symbols: List[str], data_types: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Fetch data for multiple symbols across all adapters

        Args:
            symbols: List of symbols to fetch
            data_types: Optional list of data types (default: all)

        Returns:
            Dictionary with fetched data organized by type and symbol
        """
        fetch_start = datetime.utcnow()

        if data_types is None:
            data_types = ["price", "news", "fundamental"]

        log_event(
            stage="data_fetch",
            block="orchestrator",
            level="INFO",
            msg="Starting data fetch",
            extra={"symbols": symbols, "data_types": data_types},
        )

        # Initialize results
        results = {
            "fetch_start": fetch_start.isoformat(),
            "symbols": symbols,
            "data_types": data_types,
            "raw_data": {"price": {}, "news": {}, "fundamental": {}},
            "fetch_summary": {
                "total_symbols": len(symbols),
                "successful_fetches": 0,
                "failed_fetches": 0,
                "total_records": 0,
            },
            "errors": [],
        }

        # Fetch for each data type
        for data_type in data_types:
            adapters = self.adapters_by_type.get(data_type, [])

            if not adapters:
                log_event(
                    stage="data_fetch",
                    block="orchestrator",
                    level="WARNING",
                    msg=f"No adapters for: {data_type}",
                )
                continue

            # Use first adapter for each type
            adapter = adapters[0]

            # Fetch all symbols concurrently
            tasks = [
                self._fetch_single_symbol(adapter, symbol, data_type, results)
                for symbol in symbols
            ]
            await asyncio.gather(*tasks, return_exceptions=True)

        # Calculate metrics
        fetch_end = datetime.utcnow()
        results["fetch_end"] = fetch_end.isoformat()
        results["fetch_duration_seconds"] = (fetch_end - fetch_start).total_seconds()

        log_event(
            stage="data_fetch",
            block="orchestrator",
            level="INFO",
            msg="Data fetch complete",
            extra={
                "duration": results["fetch_duration_seconds"],
                "successful": results["fetch_summary"]["successful_fetches"],
                "failed": results["fetch_summary"]["failed_fetches"],
                "records": results["fetch_summary"]["total_records"],
            },
        )

        return results

    async def _fetch_single_symbol(
        self, adapter: BaseAdapter, symbol: str, data_type: str, results: Dict[str, Any]
    ):
        """Fetch data for a single symbol using specified adapter"""
        try:
            fetch_result = await adapter.execute_ingest(symbol)

            if fetch_result.get("success"):
                data = fetch_result.get("data")

                # Store data based on type
                if data_type == "news":
                    # News: store full structure {symbol, data: [...], ...}
                    results["raw_data"][data_type][symbol] = data
                    record_count = len(data.get("data", [])) if isinstance(data, dict) else 0
                elif data_type == "price":
                    # Price: store list of records
                    if isinstance(data, list):
                        results["raw_data"][data_type][symbol] = data
                        record_count = len(data)
                    else:
                        results["raw_data"][data_type][symbol] = [data] if data else []
                        record_count = 1 if data else 0
                else:
                    # Generic: ensure list format
                    if not isinstance(data, list):
                        data = [data] if data else []
                    results["raw_data"][data_type][symbol] = data
                    record_count = len(data) if isinstance(data, list) else 1

                results["fetch_summary"]["successful_fetches"] += 1
                results["fetch_summary"]["total_records"] += record_count

                log_event(
                    stage="data_fetch",
                    block="symbol_fetch",
                    level="INFO",
                    msg=f"Fetched {data_type} for {symbol}",
                    extra={"symbol": symbol, "records": record_count},
                )
            else:
                # Handle fetch failure
                error_msg = fetch_result.get("error", "Unknown error")
                results["fetch_summary"]["failed_fetches"] += 1
                results["errors"].append({
                    "symbol": symbol,
                    "data_type": data_type,
                    "error": error_msg,
                })

                # Initialize empty structure
                if data_type == "news":
                    results["raw_data"][data_type][symbol] = {"data": []}
                else:
                    results["raw_data"][data_type][symbol] = []

                log_event(
                    stage="data_fetch",
                    block="symbol_fetch",
                    level="ERROR",
                    msg=f"Failed to fetch {data_type} for {symbol}",
                    extra={"error": error_msg},
                )

        except Exception as e:
            results["fetch_summary"]["failed_fetches"] += 1
            results["errors"].append({
                "symbol": symbol,
                "data_type": data_type,
                "error": str(e),
            })

            if data_type == "news":
                results["raw_data"][data_type][symbol] = {"data": []}
            else:
                results["raw_data"][data_type][symbol] = []

            log_event(
                stage="data_fetch",
                block="symbol_fetch",
                level="ERROR",
                msg=f"Exception fetching {data_type} for {symbol}: {str(e)}",
            )

    async def run_complete_pipeline(
        self, symbols: List[str], data_types: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Execute complete end-to-end pipeline"""
        pipeline_start = datetime.utcnow()

        log_event(
            stage="pipeline",
            block="execution",
            level="INFO",
            msg="Starting complete pipeline",
            extra={"symbols": symbols, "stages": len(self.stages)},
        )

        try:
            # Step 1: Fetch data
            fetch_results = await self.fetch_data_for_symbols(symbols, data_types)

            if fetch_results["fetch_summary"]["total_records"] == 0:
                raise ValueError("No data fetched from any source")

            # Initialize pipeline data
            pipeline_data = {
                "pipeline_start": pipeline_start.isoformat(),
                "adapters": list(self.adapters.values()),
                "symbols": symbols,
                "config": self.config,
                "raw_data": fetch_results["raw_data"],
                "fetch_summary": fetch_results["fetch_summary"],
                "fetch_errors": fetch_results.get("errors", []),
            }

            # Step 2: Execute stages
            for stage in self.stages:
                pipeline_data = await stage.execute(pipeline_data)

            # Pipeline complete
            pipeline_end = datetime.utcnow()
            pipeline_duration = (pipeline_end - pipeline_start).total_seconds()

            log_event(
                stage="pipeline",
                block="execution",
                level="INFO",
                msg="Pipeline complete",
                extra={"duration": pipeline_duration},
            )

            pipeline_data["pipeline_end"] = pipeline_end.isoformat()
            pipeline_data["pipeline_duration"] = pipeline_duration

            return pipeline_data

        except Exception as e:
            pipeline_end = datetime.utcnow()
            pipeline_duration = (pipeline_end - pipeline_start).total_seconds()

            log_event(
                stage="pipeline",
                block="execution",
                level="ERROR",
                msg=f"Pipeline failed: {str(e)}",
                extra={"duration": pipeline_duration},
            )
            raise

    async def run_smoke_test(self, symbols: List[str]) -> Dict[str, Any]:
        """Run smoke test across all adapters"""
        log_event(
            stage="smoke_test",
            block="data_farm",
            level="INFO",
            msg="Starting smoke test",
        )

        results = {
            "success": True,
            "total_tests": 0,
            "passed": 0,
            "failed": 0,
            "details": [],
        }

        for adapter_id, adapter in self.adapters.items():
            for symbol in symbols:
                results["total_tests"] += 1

                try:
                    result = await adapter.execute_ingest(symbol)

                    if result.get("success"):
                        data = result.get("data", [])
                        if isinstance(data, list):
                            record_count = len(data)
                        elif isinstance(data, dict) and "data" in data:
                            record_count = len(data.get("data", []))
                        else:
                            record_count = 1 if data else 0

                        results["passed"] += 1
                        results["details"].append({
                            "adapter_id": adapter_id,
                            "symbol": symbol,
                            "status": "PASSED",
                            "record_count": record_count,
                        })
                    else:
                        results["failed"] += 1
                        results["success"] = False
                        results["details"].append({
                            "adapter_id": adapter_id,
                            "symbol": symbol,
                            "status": "FAILED",
                            "error": result.get("error", "Unknown"),
                        })

                except Exception as e:
                    results["failed"] += 1
                    results["success"] = False
                    results["details"].append({
                        "adapter_id": adapter_id,
                        "symbol": symbol,
                        "status": "EXCEPTION",
                        "error": str(e),
                    })

        log_event(
            stage="smoke_test",
            block="data_farm",
            level="INFO",
            msg="Smoke test complete",
            extra={
                "total": results["total_tests"],
                "passed": results["passed"],
                "failed": results["failed"],
            },
        )

        return results

    def get_adapters(self) -> Dict[str, BaseAdapter]:
        """Get all loaded adapters"""
        return self.adapters

    def get_adapters_by_type(self, data_type: str) -> List[BaseAdapter]:
        """Get adapters for specific data type"""
        return self.adapters_by_type.get(data_type, [])

    def get_config(self) -> Dict[str, Any]:
        """Get loaded configuration"""
        return self.config