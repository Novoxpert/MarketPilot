"""
Base Adapter - Parent class for all data adapters with schema validation
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from datetime import datetime
import uuid
from marketpilot.utils.logger import log_event
from marketpilot.utils.schema_validator import SchemaValidator


class BaseAdapter(ABC):
    """Base class for all data adapters with enhanced logging and validation"""

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize adapter

        Args:
            config: Adapter configuration containing:
                - vendor: Data vendor name (e.g., 'yfinance', 'alphavantage')
                - id: Unique adapter identifier
                - cadence: Data collection frequency (e.g., '1min', 'daily')
                - schema_type: Type of data schema (price, news, fundamental)
        """
        self.config = config
        self.vendor = config.get("vendor", "unknown")
        self.adapter_id = config.get("id", f"adapter_{uuid.uuid4().hex[:8]}")
        self.cadence = config.get("cadence", "unknown")
        self.schema_type = config.get("schema_type", "unknown")

        # Schema validator instance
        self.validator = SchemaValidator()

        log_event(
            stage="initialization",
            block="adapter",
            level="INFO",
            msg=f"Initialized {self.__class__.__name__}",
            extra={
                "adapter_id": self.adapter_id,
                "vendor": self.vendor,
                "cadence": self.cadence,
                "schema_type": self.schema_type,
            },
        )

    async def execute_ingest(
        self,
        symbol: str,
        start: Optional[datetime] = None,
        end: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        """
        Execute ingestion with optional start/end timestamps

        Args:
            symbol: Asset symbol to ingest
            start: Optional start datetime
            end: Optional end datetime

        Returns:
            Dictionary with ingestion result
        """
        operation_id = uuid.uuid4().hex[:8]
        start_time_log = datetime.utcnow()

        log_event(
            stage="ingestion",
            block="adapter",
            level="INFO",
            msg=f"Starting ingestion for {symbol}",
            extra={
                "operation_id": operation_id,
                "adapter_id": self.adapter_id,
                "symbol": symbol,
                "vendor": self.vendor,
                "schema_type": self.schema_type,
                "start": start.isoformat() if start else None,
                "end": end.isoformat() if end else None,
            },
        )

        try:
            # Pass start/end to _execute_ingest_internal
            result = await self._execute_ingest_internal(symbol, start=start, end=end)

            duration_ms = (datetime.utcnow() - start_time_log).total_seconds() * 1000

            log_event(
                stage="ingestion",
                block="adapter",
                level="INFO",
                msg=f"Completed ingestion for {symbol}",
                extra={
                    "operation_id": operation_id,
                    "adapter_id": self.adapter_id,
                    "symbol": symbol,
                    "duration_ms": round(duration_ms, 2),
                    "success": result.get("success", False),
                    "record_count": result.get("record_count", 0),
                },
            )

            return result

        except Exception as e:
            duration_ms = (datetime.utcnow() - start_time_log).total_seconds() * 1000

            log_event(
                stage="ingestion",
                block="adapter",
                level="ERROR",
                msg=f"Ingestion failed for {symbol}: {str(e)}",
                extra={
                    "operation_id": operation_id,
                    "adapter_id": self.adapter_id,
                    "symbol": symbol,
                    "duration_ms": round(duration_ms, 2),
                    "error": str(e),
                },
            )

            return {
                "success": False,
                "error": str(e),
                "vendor": self.vendor,
                "adapter_id": self.adapter_id,
            }

    def validate_schema(self, data: Dict[str, Any]) -> bool:
        """
        Validate data against adapter's schema type

        Args:
            data: Data to validate

        Returns:
            True if valid

        Raises:
            ValueError if validation fails
        """
        if self.schema_type == "unknown":
            log_event(
                stage="validation",
                block="adapter",
                level="WARNING",
                msg="Schema type unknown, skipping validation",
                extra={"adapter_id": self.adapter_id},
            )
            return True
        #TODO:replace monk with real 
        # Create a mock record for validation
        mock_record = {
            "symbol": data.get("symbol"),
            "adapter_id": self.adapter_id,
            "vendor": self.vendor,
            "data": data,
        }

        missing_fields = self.validator.validate_record_structure(
            mock_record, self.schema_type
        )

        if missing_fields:
            error_msg = f"Schema validation failed. Missing fields: {missing_fields}"
            log_event(
                stage="validation",
                block="adapter",
                level="ERROR",
                msg=error_msg,
                extra={
                    "adapter_id": self.adapter_id,
                    "schema_type": self.schema_type,
                    "missing_fields": missing_fields,
                },
            )
            raise ValueError(error_msg)

        log_event(
            stage="validation",
            block="adapter",
            level="DEBUG",
            msg="Schema validation passed",
            extra={
                "adapter_id": self.adapter_id,
                "schema_type": self.schema_type,
            },
        )

        return True

    def log_success(self, symbol: str, record_count: int = 1):
        """Log successful ingestion"""
        log_event(
            stage="ingestion",
            block="adapter",
            level="INFO",
            msg=f"Successfully ingested data for {symbol}",
            extra={
                "adapter_id": self.adapter_id,
                "symbol": symbol,
                "record_count": record_count,
                "vendor": self.vendor,
            },
        )

    def log_error(self, symbol: str, error: str):
        """Log ingestion error"""
        log_event(
            stage="ingestion",
            block="adapter",
            level="ERROR",
            msg=f"Ingestion failed for {symbol}",
            extra={
                "adapter_id": self.adapter_id,
                "symbol": symbol,
                "error": error,
                "vendor": self.vendor,
            },
        )

    @abstractmethod
    async def _execute_ingest_internal(
        self,
        symbol: str,
        start: Optional[datetime] = None,
        end: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        """
        Internal ingestion logic to be implemented by subclasses

        Args:
            symbol: Asset symbol to ingest
            start: Optional start datetime
            end: Optional end datetime

        Returns:
            Dictionary with ingestion result
        """
        pass
