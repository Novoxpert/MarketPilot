"""
Base Adapter for Data Farm
All adapters inherit from this class
"""

from abc import ABC, abstractmethod
from typing import Dict, Any
from datetime import datetime
import uuid
from marketpilot.utils.logger import log_event
from marketpilot.config.config_loader import validate_data_columns


class BaseAdapter(ABC):
    """Base class for all data adapters with enhanced logging"""

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize adapter with configuration

        Args:
            config: Adapter configuration containing:
                - vendor: Vendor name (e.g., 'yfinance', 'alphavantage')
                - id: Unique adapter ID
                - cadence: Update frequency (e.g., '1min', 'daily')
                - schema_type: Schema type for validation (price, news, fundamental)
        """
        self.vendor = config.get("vendor", "unknown")
        self.adapter_id = config.get("id", "unknown")
        self.cadence = config.get("cadence", "daily")
        self.schema_type = config.get("schema_type", "unknown")

        log_event(
            stage="ingestion",
            block=f"{self.vendor}_adapter",
            level="INFO",
            msg=f"Adapter initialized: {self.adapter_id}",
            extra={"cadence": self.cadence, "schema_type": self.schema_type},
        )

    async def execute_ingest(self, symbol: str) -> Dict[str, Any]:
        """
        Execute data ingestion with enhanced logging

        Args:
            symbol: Asset symbol (e.g., 'AAPL', 'TSLA')

        Returns:
            Dictionary containing ingested data
        """
        # Generate unique operation ID
        operation_id = str(uuid.uuid4())[:8]
        start_time = datetime.now()

        # Log ingestion start
        log_event(
            stage="ingestion",
            block=f"{self.vendor}_adapter",
            level="INFO",
            msg=f"Starting ingestion for {symbol}",
            extra={
                "operation_id": operation_id,
                "adapter_id": self.adapter_id,
                "symbol": symbol,
                "timestamp": start_time.isoformat(),
            },
        )

        try:
            # Execute the actual ingestion
            result = await self._execute_ingest_internal(symbol)

            end_time = datetime.now()
            duration_ms = (end_time - start_time).total_seconds() * 1000

            # Log successful ingestion with metrics
            record_count = 1 if result.get("success") else 0

            log_event(
                stage="ingestion",
                block=f"{self.vendor}_adapter",
                level="INFO",
                msg=f"Completed ingestion for {symbol}",
                extra={
                    "operation_id": operation_id,
                    "adapter_id": self.adapter_id,
                    "symbol": symbol,
                    "duration_ms": round(duration_ms, 2),
                    "records_processed": record_count,
                    "success_flag": result.get("success", False),
                    "timestamp": end_time.isoformat(),
                },
            )

            return result

        except Exception as e:
            end_time = datetime.now()
            duration_ms = (end_time - start_time).total_seconds() * 1000

            # Log ingestion failure
            log_event(
                stage="ingestion",
                block=f"{self.vendor}_adapter",
                level="ERROR",
                msg=f"Failed ingestion for {symbol}: {str(e)}",
                extra={
                    "operation_id": operation_id,
                    "adapter_id": self.adapter_id,
                    "symbol": symbol,
                    "duration_ms": round(duration_ms, 2),
                    "success_flag": False,
                    "error_type": type(e).__name__,
                    "error_message": str(e),
                    "timestamp": end_time.isoformat(),
                },
            )

            return {"success": False, "error": str(e), "vendor": self.vendor}

    @abstractmethod
    async def _execute_ingest_internal(self, symbol: str) -> Dict[str, Any]:
        """
        Execute data ingestion for a symbol (to be implemented by subclasses)

        Args:
            symbol: Asset symbol (e.g., 'AAPL', 'TSLA')

        Returns:
            Dictionary containing ingested data
        """
        pass

    def validate_schema(self, data: Dict[str, Any]) -> bool:
        """
        Validate data against schema

        Args:
            data: Data to validate

        Returns:
            True if valid

        Raises:
            ConfigError: If validation fails
        """
        try:
            validate_data_columns(data, self.schema_type)
            log_event(
                stage="ingestion",
                block=f"{self.vendor}_adapter",
                level="INFO",
                msg=f"Schema validation passed for {self.schema_type}",
                extra={"adapter_id": self.adapter_id},
            )
            return True
        except Exception as e:
            log_event(
                stage="ingestion",
                block=f"{self.vendor}_adapter",
                level="ERROR",
                msg=f"Schema validation failed: {str(e)}",
                extra={"adapter_id": self.adapter_id, "schema_type": self.schema_type},
            )
            raise

    def log_success(self, symbol: str, record_count: int):
        """Log successful ingestion (deprecated - use execute_ingest logging)"""
        log_event(
            stage="ingestion",
            block=f"{self.vendor}_adapter",
            level="INFO",
            msg=f"Successfully ingested data for {symbol}",
            extra={
                "symbol": symbol,
                "records": record_count,
                "adapter_id": self.adapter_id,
            },
        )

    def log_error(self, symbol: str, error: str):
        """Log ingestion error (deprecated - use execute_ingest logging)"""
        log_event(
            stage="ingestion",
            block=f"{self.vendor}_adapter",
            level="ERROR",
            msg=f"Failed to ingest data for {symbol}",
            extra={"symbol": symbol, "error": error, "adapter_id": self.adapter_id},
        )
