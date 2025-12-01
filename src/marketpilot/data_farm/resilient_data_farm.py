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
load_dotenv()


class ResilientDataFarm:
    """
    Main orchestrator for Data Farm pipeline
    
    Architecture:
    - Adapters: Created ONCE during initialization
    - HealthCheck: Tests API /health endpoints ONCE per pipeline run
    - DataCollection: Uses existing adapters to fetch data
    - Processing Stages: Clean, align, deduplicate, validate, export
    """

    def __init__(
        self, 
        config_path: str = "src/marketpilot/configs/data/data_farm_config.yml"
    ):
        """
        Initialize ResilientDataFarm (runs ONCE)

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
        self.adapters: List[BaseAdapter] = []

        # Initialize pipeline stages (created once)
        self.stages = [
            HealthCheckStage(),        # Step 1: Test API health (once per run)
            DataCollectionStage(),     # Step 2: Fetch data using adapters
            NaNProcessingStage(),      # Step 3: Clean missing values
            TemporalAlignmentStage(),  # Step 4: Normalize timestamps
            DeduplicationStage(),      # Step 5: Remove duplicates
            QualityAssuranceStage(),   # Step 6: Validate quality
            DataExportStage(),         # Step 7: Export to Parquet
        ]

        # Initialize components
        self._initialize_components()
        self._initialize_adapters()

        log_event(
            stage="initialization",
            block="data_farm",
            level="INFO",
            msg="ResilientDataFarm initialized successfully",
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
        """
        Initialize all adapters from configuration (runs ONCE)
        
        Adapters are reused across multiple pipeline runs
        """
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
                self.adapters.append(adapter)

                log_event(
                    stage="initialization",
                    block="adapters",
                    level="INFO",
                    msg=f"Loaded adapter: {adapter_id}",
                    extra={
                        "type": adapter_type, 
                        "vendor": adapter_config.get("vendor")
                    },
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
            extra={"total_adapters": len(self.adapters)},
        )

    async def run_complete_pipeline(
        self, 
        symbols: List[str],
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        """
        Execute complete end-to-end pipeline
        
        Flow:
        1. HealthCheck: Test API /health endpoints (ONCE)
        2. DataCollection: Fetch data for all symbols (uses existing adapters)
        3. NaN Processing: Clean missing values
        4. Temporal Alignment: Normalize timestamps
        5. Deduplication: Remove duplicates
        6. Quality Assurance: Validate data quality
        7. Export: Save to Parquet files (Asset-First structure)
        
        Args:
            symbols: List of symbols to process
            start_date: Optional start date for data collection
            end_date: Optional end date for data collection
        """
        pipeline_start = datetime.utcnow()

        log_event(
            stage="pipeline",
            block="execution",
            level="INFO",
            msg="Starting complete pipeline",
            extra={
                "symbols": symbols,
                "symbol_count": len(symbols),
                "stages": len(self.stages),
                "adapters": len(self.adapters),
                "start_date": start_date.isoformat() if start_date else None,
                "end_date": end_date.isoformat() if end_date else None,
            },
        )

        try:
            # Initialize pipeline data
            pipeline_data = {
                "pipeline_start": pipeline_start.isoformat(),
                "adapters": self.adapters,  # Pass existing adapters to stages
                "symbols": symbols,
                "config": self.config,
                "start_date": start_date,  # Optional time range
                "end_date": end_date,
            }

            # Execute all stages in sequence
            for stage in self.stages:
                try:
                    pipeline_data = await stage.execute(pipeline_data)
                    
                    # Check health status after health check
                    if isinstance(stage, HealthCheckStage):
                        health = pipeline_data.get("health_check", {})
                        status = health.get("overall_status")
                        
                        if status == "critical":
                            raise RuntimeError(
                                "Health check failed: APIs are not available"
                            )
                        elif status == "degraded":
                            log_event(
                                stage="pipeline",
                                block="health_check",
                                level="WARNING",
                                msg="System is degraded but continuing",
                                extra={
                                    "healthy_apis": health.get("apis_healthy"),
                                    "total_apis": health.get("apis_checked"),
                                },
                            )
                    
                    # Check if data collection succeeded
                    if isinstance(stage, DataCollectionStage):
                        summary = pipeline_data.get("collection_summary", {})
                        if summary.get("successful", 0) == 0:
                            raise RuntimeError(
                                "Data collection failed: No data fetched from any adapter"
                            )
                
                except Exception as stage_error:
                    log_event(
                        stage="pipeline",
                        block="execution",
                        level="ERROR",
                        msg=f"Stage {stage.stage_name} failed: {str(stage_error)}",
                        extra={"stage": stage.stage_name, "error": str(stage_error)},
                    )
                    raise

            # Pipeline complete
            pipeline_end = datetime.utcnow()
            pipeline_duration = (pipeline_end - pipeline_start).total_seconds()

            log_event(
                stage="pipeline",
                block="execution",
                level="INFO",
                msg="Pipeline completed successfully",
                extra={
                    "duration_seconds": pipeline_duration,
                    "symbols_processed": len(symbols),
                    "records_exported": pipeline_data.get("export_stats", {}).get(
                        "records_exported", 0
                    ),
                },
            )

            pipeline_data["pipeline_end"] = pipeline_end.isoformat()
            pipeline_data["pipeline_duration"] = pipeline_duration
            pipeline_data["pipeline_success"] = True

            return pipeline_data

        except Exception as e:
            pipeline_end = datetime.utcnow()
            pipeline_duration = (pipeline_end - pipeline_start).total_seconds()

            log_event(
                stage="pipeline",
                block="execution",
                level="ERROR",
                msg=f"Pipeline failed: {str(e)}",
                extra={"duration": pipeline_duration, "error": str(e)},
            )
            
            return {
                "pipeline_success": False,
                "pipeline_duration": pipeline_duration,
                "error": str(e),
            }

    async def run_smoke_test(
            self, 
            symbols: List[str], 
            start: Optional[datetime] = None, 
            end: Optional[datetime] = None
        ) -> Dict[str, Any]:
        """
        Run quick smoke test (optional pre-flight check)
        
        Tests each adapter with a single symbol to verify basic functionality
        """
        log_event(
            stage="smoke_test",
            block="data_farm",
            level="INFO",
            msg="Starting smoke test",
            extra={
                "symbols": symbols,
                "adapters": len(self.adapters),
                "start": start.isoformat() if start else None,
                "end": end.isoformat() if end else None,
            },
        )

        results = {
            "success": True,
            "total_tests": 0,
            "passed": 0,
            "failed": 0,
            "details": [],
        }

        for adapter in self.adapters:
            # Test with first symbol only
            test_symbol = symbols[0] if symbols else "AAPL"
            results["total_tests"] += 1

            try:
                # فقط وقتی start/end مقدار دارند پاس بده
                kwargs = {"symbol": test_symbol}
                if start is not None:
                    kwargs["start"] = start
                if end is not None:
                    kwargs["end"] = end

                result = await adapter.execute_ingest(**kwargs)

                if result.get("success"):
                    record_count = result.get("record_count", 0)
                    results["passed"] += 1
                    results["details"].append({
                        "adapter_id": adapter.adapter_id,
                        "symbol": test_symbol,
                        "status": "PASSED",
                        "record_count": record_count,
                    })
                else:
                    results["failed"] += 1
                    results["success"] = False
                    results["details"].append({
                        "adapter_id": adapter.adapter_id,
                        "symbol": test_symbol,
                        "status": "FAILED",
                        "error": result.get("error", "Unknown"),
                    })

            except Exception as e:
                results["failed"] += 1
                results["success"] = False
                results["details"].append({
                    "adapter_id": adapter.adapter_id,
                    "symbol": test_symbol,
                    "status": "EXCEPTION",
                    "error": str(e),
                })

        log_event(
            stage="smoke_test",
            block="data_farm",
            level="INFO" if results["success"] else "WARNING",
            msg="Smoke test complete",
            extra={
                "total": results["total_tests"],
                "passed": results["passed"],
                "failed": results["failed"],
            },
        )

        return results

    def get_adapters(self) -> List[BaseAdapter]:
        """Get all loaded adapters"""
        return self.adapters

    def get_config(self) -> Dict[str, Any]:
        """Get loaded configuration"""
        return self.config


if __name__ == "__main__":
    print("\n🚀 ResilientDataFarm - Quick Test\n")

    async def _main():
        # Create the orchestrator (adapters created here)
        farm = ResilientDataFarm()

        # Define test symbols
        test_symbols = ["BINANCE:BTCUSDT.P", "BINANCE:ETHUSDT.P"]

        # Optional: Run smoke test first
        # print(">>> Running smoke test...",test_symbols[:1])
        # start = None
        # end = None
        # start = datetime.strptime("20251201-0708", "%Y%m%d-%H%M")
        # end   = datetime.strptime("20251201-0709", "%Y%m%d-%H%M")
        # smoke_results = await farm.run_smoke_test(test_symbols[:1],start,end)
        # print(f"Smoke test: {smoke_results['passed']}/{smoke_results['total_tests']} passed\n")

        # if not smoke_results["success"]:
        #     print("❌ Smoke test failed. Fix adapters before running pipeline.")
        #     return

        # Run full pipeline
        print(">>> Running full pipeline...")
        results = await farm.run_complete_pipeline(test_symbols)

        if results.get("pipeline_success"):
            print("\n✅ Pipeline completed successfully")
            print(f"Duration: {results['pipeline_duration']:.2f}s")
            print(f"Records: {results.get('export_stats', {}).get('records_exported', 0)}")
        else:
            print("\n❌ Pipeline failed")
            print(f"Error: {results.get('error')}")

    asyncio.run(_main())