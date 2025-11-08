"""
ResilientDataFarm - Main orchestrator for all adapters
Entry point for Market Pilot data ingestion system
"""

from typing import Dict, Any, List
from pathlib import Path
from ...config.config_loader import load_config
from ..utils.logger import log_event, setup_logging
from adapters.base_adapter import BaseAdapter
from adapters.price_adapter import ResilientPriceAdapter
from adapters.news_adapter import ResilientNewsAdapter
from adapters.fundamental_adapter import ResilientFundamentalAdapter


class ResilientDataFarm:
    """Main orchestrator class for Data Farm pipeline"""

    def __init__(self, config_path: str = "data_farm/config/data_farm_config.yaml"):
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

        # Create output directories if specified
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

        # Get adapters config
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
                # Get the appropriate adapter class
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

    async def run_smoke_test(self, symbols: List[str]) -> Dict[str, Any]:
        """
        Run smoke test across all adapters for given symbols

        Args:
            symbols: List of asset symbols to test (e.g., ['AAPL', 'NVDA', 'TSLA'])

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

        # Run each adapter for each symbol
        for adapter in self.adapters:
            for symbol in symbols:
                results["total_tests"] += 1

                try:
                    # Execute adapter ingestion
                    result = await adapter.execute_ingest(symbol)

                    if result.get("success"):
                        results["passed"] += 1
                        results["details"].append(
                            {
                                "adapter_id": adapter.adapter_id,
                                "symbol": symbol,
                                "status": "✅ PASSED",
                            }
                        )
                    else:
                        results["failed"] += 1
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
                            "status": "❌ EXCEPTION",
                            "error": str(e),
                        }
                    )

                    log_event(
                        stage="smoke_test",
                        block="data_farm",
                        level="ERROR",
                        msg="Exception during smoke test",
                        extra={
                            "adapter_id": adapter.adapter_id,
                            "symbol": symbol,
                            "error": str(e),
                        },
                    )

        # Final summary
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
