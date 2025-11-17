"""
ResilientDataFarm
"""

from typing import Dict, Any, List
from pathlib import Path
from datetime import datetime
from marketpilot.config.config_loader import load_config
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

#  NEW: Import schema validator
from marketpilot.utils.schema_validator import validate_pipeline_stages


class ResilientDataFarm:
    """Main orchestrator class for Data Farm pipeline with validation"""

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
        self.adapters: List[BaseAdapter] = []

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
                self.adapters.append(adapter)

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
                    extra={"adapter_id": adapter_id, "adapter_type": adapter_type},
                )

        log_event(
            stage="initialization",
            block="adapters",
            level="INFO",
            msg="Adapter initialization complete",
            extra={"total_adapters": len(self.adapters)},
        )

    async def _execute_complete_pipeline(self, symbols: List[str]) -> Dict[str, Any]:
        """
        Execute complete end-to-end pipeline with all stages

        Args:
            symbols: List of symbols to process

        Returns:
            Complete pipeline results with validation report
        """
        pipeline_start = datetime.now()

        log_event(
            stage="pipeline",
            block="execution",
            level="INFO",
            msg="Starting complete pipeline execution",
            extra={
                "symbols": symbols,
                "total_stages": len(self.stages),
            },
        )

        # Initialize pipeline data
        pipeline_data = {
            "pipeline_start": pipeline_start.isoformat(),
            "adapters": self.adapters,
            "symbols": symbols,
            "config": self.config,
        }

        try:
            # Execute each stage sequentially
            for stage in self.stages:
                log_event(
                    stage="pipeline",
                    block="execution",
                    level="INFO",
                    msg=f"Executing stage: {stage.stage_name}",
                )

                # Execute stage
                pipeline_data = await stage.execute(pipeline_data)

            #  NEW: Validate pipeline schema consistency
            log_event(
                stage="pipeline",
                block="validation",
                level="INFO",
                msg="Running schema validation",
            )

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
                        "stages_validated": len(validation_report["stages_validated"]),
                        "warnings": len(validation_report["warnings"]),
                    },
                )
            else:
                log_event(
                    stage="pipeline",
                    block="validation",
                    level="ERROR",
                    msg="Schema validation FAILED",
                    extra={
                        "errors": validation_report["errors"],
                        "warnings": validation_report["warnings"],
                    },
                )

            # Pipeline complete
            pipeline_end = datetime.now()
            pipeline_duration = (pipeline_end - pipeline_start).total_seconds()

            log_event(
                stage="pipeline",
                block="execution",
                level="INFO",
                msg="Complete pipeline execution finished",
                extra={
                    "total_duration_seconds": pipeline_duration,
                    "stages_completed": len(self.stages),
                    "validation_passed": validation_report["validation_passed"],
                },
            )

            pipeline_data["pipeline_end"] = pipeline_end.isoformat()
            pipeline_data["pipeline_duration"] = pipeline_duration

            return pipeline_data

        except Exception as e:
            pipeline_end = datetime.now()
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

    async def run_complete_pipeline(self, symbols: List[str]) -> Dict[str, Any]:
        """
        Public method to run complete end-to-end pipeline

        Args:
            symbols: List of symbols to process

        Returns:
            Pipeline results with validation report
        """
        return await self._execute_complete_pipeline(symbols)

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

        for adapter in self.adapters:
            for symbol in symbols:
                results["total_tests"] += 1

                try:
                    result = await adapter.execute_ingest(symbol)

                    if result.get("success"):
                        results["passed"] += 1
                        results["details"].append(
                            {
                                "adapter_id": adapter.adapter_id,
                                "symbol": symbol,
                                "status": " PASSED",
                            }
                        )
                    else:
                        results["failed"] += 1
                        results["details"].append(
                            {
                                "adapter_id": adapter.adapter_id,
                                "symbol": symbol,
                                "status": " FAILED",
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
                            "status": " EXCEPTION",
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

    def get_adapters(self) -> List[BaseAdapter]:
        """Get list of all loaded adapters"""
        return self.adapters

    def get_config(self) -> Dict[str, Any]:
        """Get loaded configuration"""
        return self.config
