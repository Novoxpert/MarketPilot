"""
ResilientDataFarm - Complete implementation with data fetching and storage
"""

from typing import Dict, Any, List, Optional
from pathlib import Path
from datetime import datetime
import asyncio
from marketpilot.utils.config_loader_ import load_config
from marketpilot.utils.logger import log_event, setup_logging
from marketpilot.adapters.base_adapter import BaseAdapter
from marketpilot.adapters.price_adapter import ResilientPriceAdapter
from marketpilot.adapters.news_adapter import ResilientNewsAdapter
from marketpilot.adapters.fundamental_adapter import ResilientFundamentalAdapter

# Import all pipeline stages
from marketpilot.data_farm.stages.health_check import HealthCheckStage
from marketpilot.data_farm.stages.data_collection import DataCollectionStage
from marketpilot.data_farm.stages.nan_processing import NaNProcessingStage
from marketpilot.data_farm.stages.temporal_alignment import TemporalAlignmentStage
from marketpilot.data_farm.stages.deduplication import DeduplicationStage
from marketpilot.data_farm.stages.quality_assurance import QualityAssuranceStage
from marketpilot.data_farm.stages.data_export import DataExportStage

# Import schema validator
from marketpilot.utils.schema_validator import validate_pipeline_stages


class ResilientDataFarm:
    """Main orchestrator class for Data Farm pipeline with complete data fetching"""

    def __init__(
        self, config_path: str = "src/marketpilot/config/data_farm_config.yaml"
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
        self.adapters: Dict[str, BaseAdapter] = {}  # Changed to dict for easy lookup
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
            msg="ResilientDataFarm initialization complete",
            extra={
                "adapters_loaded": len(self.adapters),
                "stages_loaded": len(self.stages),
                "config_loaded": bool(self.config),
            },
        )

    def _initialize_components(self):
        """Initialize core components (logging, directories)"""
        log_event(
            stage="initialization",
            block="components",
            level="INFO",
            msg="Initializing core components",
        )

        # Setup logging system
        log_level = self.config.get("logging", {}).get("level", "INFO")
        setup_logging(log_level)

        # Create output directories
        output_dir = self.config.get("output", {}).get("base_dir", "data/output")
        Path(output_dir).mkdir(parents=True, exist_ok=True)

        log_event(
            stage="initialization",
            block="components",
            level="INFO",
            msg="Core components initialized",
            extra={"log_level": log_level, "output_dir": output_dir},
        )

    def _initialize_adapters(self):
        """Initialize all adapters from configuration"""
        log_event(
            stage="initialization",
            block="adapters",
            level="INFO",
            msg="Loading adapters from configuration",
        )

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
            adapter_type = adapter_config.get("type", "unknown")
            adapter_id = adapter_config.get("id", "unknown")

            try:
                adapter_class = adapter_classes.get(adapter_type)

                if not adapter_class:
                    log_event(
                        stage="initialization",
                        block="adapters",
                        level="ERROR",
                        msg=f"Unknown adapter type: {adapter_type}",
                        extra={"adapter_id": adapter_id},
                    )
                    continue

                # Create adapter instance
                adapter = adapter_class(adapter_config)

                # Store by ID and type
                self.adapters[adapter_id] = adapter
                self.adapters_by_type[adapter_type].append(adapter)

                log_event(
                    stage="initialization",
                    block="adapters",
                    level="INFO",
                    msg="Adapter loaded successfully",
                    extra={
                        "adapter_id": adapter_id,
                        "adapter_type": adapter_type,
                        "vendor": adapter_config.get("vendor", "unknown"),
                    },
                )

            except Exception as e:
                log_event(
                    stage="initialization",
                    block="adapters",
                    level="ERROR",
                    msg=f"Failed to load adapter: {str(e)}",
                    extra={
                        "adapter_id": adapter_id,
                        "adapter_type": adapter_type,
                        "error": str(e),
                    },
                )

        log_event(
            stage="initialization",
            block="adapters",
            level="INFO",
            msg="Adapter initialization complete",
            extra={
                "total_adapters": len(self.adapters),
                "price_adapters": len(self.adapters_by_type["price"]),
                "news_adapters": len(self.adapters_by_type["news"]),
                "fundamental_adapters": len(self.adapters_by_type["fundamental"]),
            },
        )

    async def fetch_data_for_symbols(
        self, symbols: List[str], data_types: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Fetch data for multiple symbols across all adapters

        Args:
            symbols: List of symbols to fetch (e.g., ["BINANCE:BTCUSDT.P"])
            data_types: Optional list of data types to fetch (default: all)

        Returns:
            Dictionary containing fetched data organized by type and symbol
        """
        fetch_start = datetime.utcnow()

        # Default to all data types if not specified
        if data_types is None:
            data_types = ["price", "news", "fundamental"]

        log_event(
            stage="data_fetch",
            block="orchestrator",
            level="INFO",
            msg="Starting data fetch operation",
            extra={
                "symbols": symbols,
                "data_types": data_types,
                "symbol_count": len(symbols),
            },
        )

        # Initialize results structure
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

        # Fetch data for each type
        for data_type in data_types:
            adapters = self.adapters_by_type.get(data_type, [])

            if not adapters:
                log_event(
                    stage="data_fetch",
                    block="orchestrator",
                    level="WARNING",
                    msg=f"No adapters available for data type: {data_type}",
                )
                continue

            # Use first adapter for each type (can be enhanced for fallback logic)
            adapter = adapters[0]

            log_event(
                stage="data_fetch",
                block="orchestrator",
                level="INFO",
                msg=f"Fetching {data_type} data using adapter: {adapter.adapter_id}",
            )

            # Fetch data for all symbols concurrently
            fetch_tasks = [
                self._fetch_single_symbol(adapter, symbol, data_type, results)
                for symbol in symbols
            ]

            await asyncio.gather(*fetch_tasks, return_exceptions=True)

        # Calculate final metrics
        fetch_end = datetime.utcnow()
        fetch_duration = (fetch_end - fetch_start).total_seconds()

        results["fetch_end"] = fetch_end.isoformat()
        results["fetch_duration_seconds"] = fetch_duration

        log_event(
            stage="data_fetch",
            block="orchestrator",
            level="INFO",
            msg="Data fetch operation complete",
            extra={
                "duration_seconds": fetch_duration,
                "successful": results["fetch_summary"]["successful_fetches"],
                "failed": results["fetch_summary"]["failed_fetches"],
                "total_records": results["fetch_summary"]["total_records"],
            },
        )

        return results

    async def _fetch_single_symbol(
        self, adapter: BaseAdapter, symbol: str, data_type: str, results: Dict[str, Any]
    ):
        """
        Fetch data for a single symbol using specified adapter

        Args:
            adapter: Adapter instance to use
            symbol: Symbol to fetch
            data_type: Type of data (price, news, fundamental)
            results: Results dictionary to update
        """
        try:
            log_event(
                stage="data_fetch",
                block="symbol_fetch",
                level="DEBUG",
                msg=f"Fetching {data_type} data for {symbol}",
                extra={
                    "adapter_id": adapter.adapter_id,
                    "symbol": symbol,
                    "data_type": data_type,
                },
            )

            # Execute fetch
            fetch_result = await adapter.execute_ingest(symbol)

            if fetch_result.get("success"):
                # Get data from result
                data = fetch_result.get("data", [])

                # Handle both list and dict responses
                if not isinstance(data, list):
                    data = [data] if data else []

                # Store data
                results["raw_data"][data_type][symbol] = data

                # Update metrics
                record_count = len(data) if isinstance(data, list) else 1
                results["fetch_summary"]["successful_fetches"] += 1
                results["fetch_summary"]["total_records"] += record_count

                log_event(
                    stage="data_fetch",
                    block="symbol_fetch",
                    level="INFO",
                    msg=f"Successfully fetched {data_type} data for {symbol}",
                    extra={
                        "symbol": symbol,
                        "data_type": data_type,
                        "record_count": record_count,
                    },
                )
            else:
                # Log failure
                error_msg = fetch_result.get("error", "Unknown error")
                results["fetch_summary"]["failed_fetches"] += 1
                results["errors"].append(
                    {
                        "symbol": symbol,
                        "data_type": data_type,
                        "adapter_id": adapter.adapter_id,
                        "error": error_msg,
                    }
                )

                # Initialize empty list for failed fetch
                results["raw_data"][data_type][symbol] = []

                log_event(
                    stage="data_fetch",
                    block="symbol_fetch",
                    level="ERROR",
                    msg=f"Failed to fetch {data_type} data for {symbol}",
                    extra={
                        "symbol": symbol,
                        "data_type": data_type,
                        "error": error_msg,
                    },
                )

        except Exception as e:
            results["fetch_summary"]["failed_fetches"] += 1
            results["errors"].append(
                {
                    "symbol": symbol,
                    "data_type": data_type,
                    "adapter_id": adapter.adapter_id,
                    "error": str(e),
                }
            )

            # Initialize empty list for exception
            results["raw_data"][data_type][symbol] = []

            log_event(
                stage="data_fetch",
                block="symbol_fetch",
                level="ERROR",
                msg=f"Exception while fetching {data_type} data for {symbol}",
                extra={"symbol": symbol, "data_type": data_type, "error": str(e)},
            )

    async def _execute_complete_pipeline(
        self, symbols: List[str], data_types: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Execute complete end-to-end pipeline with all stages

        Args:
            symbols: List of symbols to process
            data_types: Optional list of data types to fetch

        Returns:
            Complete pipeline results with validation report
        """
        pipeline_start = datetime.utcnow()

        log_event(
            stage="pipeline",
            block="execution",
            level="INFO",
            msg="Starting complete pipeline execution",
            extra={
                "symbols": symbols,
                "data_types": data_types,
                "total_stages": len(self.stages),
            },
        )

        try:
            # Step 1: Fetch data from API
            log_event(
                stage="pipeline",
                block="execution",
                level="INFO",
                msg="Step 1: Fetching data from API",
            )

            fetch_results = await self.fetch_data_for_symbols(symbols, data_types)

            # Check if fetch was successful
            if fetch_results["fetch_summary"]["failed_fetches"] > 0:
                log_event(
                    stage="pipeline",
                    block="execution",
                    level="WARNING",
                    msg="Some data fetches failed",
                    extra={
                        "failed_count": fetch_results["fetch_summary"][
                            "failed_fetches"
                        ],
                        "errors": fetch_results["errors"],
                    },
                )

            # Check if we have any data at all
            if fetch_results["fetch_summary"]["total_records"] == 0:
                log_event(
                    stage="pipeline",
                    block="execution",
                    level="ERROR",
                    msg="No data fetched - cannot proceed with pipeline",
                    extra={
                        "symbols": symbols,
                        "data_types": data_types,
                        "errors": fetch_results["errors"],
                    },
                )
                raise ValueError("No data fetched from any source")

            # Initialize pipeline data with fetched data
            pipeline_data = {
                "pipeline_start": pipeline_start.isoformat(),
                "adapters": list(self.adapters.values()),
                "symbols": symbols,
                "config": self.config,
                "raw_data": fetch_results["raw_data"],
                "fetch_summary": fetch_results["fetch_summary"],
                "fetch_errors": fetch_results.get("errors", []),
            }

            # Step 2: Execute each stage sequentially
            log_event(
                stage="pipeline",
                block="execution",
                level="INFO",
                msg="Step 2: Executing pipeline stages",
            )

            for stage in self.stages:
                log_event(
                    stage="pipeline",
                    block="execution",
                    level="INFO",
                    msg=f"Executing stage: {stage.stage_name}",
                )

                # Execute stage
                pipeline_data = await stage.execute(pipeline_data)

                # Log stage completion
                log_event(
                    stage="pipeline",
                    block="execution",
                    level="INFO",
                    msg=f"Completed stage: {stage.stage_name}",
                )

            # Step 3: Validate pipeline schema consistency
            log_event(
                stage="pipeline",
                block="validation",
                level="INFO",
                msg="Step 3: Running schema validation",
            )

            try:
                validation_report = validate_pipeline_stages(pipeline_data)
                pipeline_data["validation_report"] = validation_report

                # Log validation results
                if validation_report["validation_passed"]:
                    log_event(
                        stage="pipeline",
                        block="validation",
                        level="INFO",
                        msg="Schema validation PASSED",
                        extra={
                            "stages_validated": len(
                                validation_report.get("stages_validated", [])
                            ),
                            "warnings": len(validation_report.get("warnings", [])),
                        },
                    )
                else:
                    log_event(
                        stage="pipeline",
                        block="validation",
                        level="ERROR",
                        msg="Schema validation FAILED",
                        extra={
                            "errors": validation_report.get("errors", []),
                            "warnings": validation_report.get("warnings", []),
                        },
                    )
            except Exception as validation_error:
                log_event(
                    stage="pipeline",
                    block="validation",
                    level="WARNING",
                    msg=f"Schema validation error (non-critical): {str(validation_error)}",
                    extra={"error": str(validation_error)},
                )
                # Create a minimal validation report
                pipeline_data["validation_report"] = {
                    "validation_passed": False,
                    "errors": [f"Validation failed: {str(validation_error)}"],
                    "warnings": [],
                    "stages_validated": [],
                }

            # Pipeline complete
            pipeline_end = datetime.utcnow()
            pipeline_duration = (pipeline_end - pipeline_start).total_seconds()

            log_event(
                stage="pipeline",
                block="execution",
                level="INFO",
                msg="Complete pipeline execution finished",
                extra={
                    "total_duration_seconds": pipeline_duration,
                    "stages_completed": len(self.stages),
                    "validation_passed": pipeline_data.get("validation_report", {}).get(
                        "validation_passed", False
                    ),
                    "total_records_processed": fetch_results["fetch_summary"][
                        "total_records"
                    ],
                },
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
                msg=f"Pipeline execution failed: {str(e)}",
                extra={
                    "duration_seconds": pipeline_duration,
                    "error": str(e),
                },
            )

            raise

    async def run_complete_pipeline(
        self, symbols: List[str], data_types: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Public method to run complete end-to-end pipeline

        Args:
            symbols: List of symbols to process
            data_types: Optional list of data types to fetch (default: all)

        Returns:
            Pipeline results with validation report
        """
        return await self._execute_complete_pipeline(symbols, data_types)

    async def run_smoke_test(self, symbols: List[str]) -> Dict[str, Any]:
        """
        Run smoke test across all adapters for given symbols

        Args:
            symbols: List of asset symbols to test

        Returns:
            Dictionary with test results
        """
        log_event(
            stage="smoke_test",
            block="data_farm",
            level="INFO",
            msg="Starting smoke test",
            extra={"symbols": symbols, "adapter_count": len(self.adapters)},
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
                        # Get record count
                        data = result.get("data", [])
                        if isinstance(data, list):
                            record_count = len(data)
                        else:
                            record_count = 1 if data else 0

                        results["passed"] += 1
                        results["details"].append(
                            {
                                "adapter_id": adapter.adapter_id,
                                "symbol": symbol,
                                "status": "✅ PASSED",
                                "record_count": record_count,
                            }
                        )
                    else:
                        results["failed"] += 1
                        results["success"] = False
                        results["details"].append(
                            {
                                "adapter_id": adapter.adapter_id,
                                "symbol": symbol,
                                "status": "❌ FAILED",
                                "error": result.get("error", "Unknown"),
                            }
                        )

                except Exception as e:
                    results["failed"] += 1
                    results["success"] = False
                    results["details"].append(
                        {
                            "adapter_id": adapter.adapter_id,
                            "symbol": symbol,
                            "status": "⚠️ EXCEPTION",
                            "error": str(e),
                        }
                    )

        log_event(
            stage="smoke_test",
            block="data_farm",
            level="INFO" if results["failed"] == 0 else "WARNING",
            msg="Smoke test completed",
            extra={
                "total": results["total_tests"],
                "passed": results["passed"],
                "failed": results["failed"],
            },
        )

        return results

    def get_adapters(self) -> Dict[str, BaseAdapter]:
        """Get dictionary of all loaded adapters"""
        return self.adapters

    def get_adapters_by_type(self, data_type: str) -> List[BaseAdapter]:
        """
        Get adapters for specific data type

        Args:
            data_type: Type of data (price, news, fundamental)

        Returns:
            List of adapters for that type
        """
        return self.adapters_by_type.get(data_type, [])

    def get_config(self) -> Dict[str, Any]:
        """Get loaded configuration"""
        return self.config
