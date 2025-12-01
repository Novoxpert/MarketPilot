"""
Base Adapter - Parent class for all data adapters
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from datetime import datetime
import uuid
from marketpilot.utils.logger import log_event


class BaseAdapter(ABC):
    """Base class for all data adapters"""

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize adapter

        Args:
            config: Adapter configuration containing:
                - vendor: Data vendor name (e.g., 'yfinance', 'alphavantage')
                - id: Unique adapter identifier (price_internal_001)
                - cadence: Data collection frequency (e.g., '1min', 'daily')
                - schema_type: Type of data schema (price, news, fundamental)
        """
        self.config = config
        self.vendor = config.get("vendor", "unknown")
        self.adapter_id = config.get("id", f"adapter_{uuid.uuid4().hex[:8]}")
        self.cadence = config.get("cadence", "unknown")
        self.schema_type = config.get("schema_type", "unknown")

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
        Execute ingestion with timing and error handling

        Args:
            symbol: Asset symbol to ingest
            start: Optional start datetime
            end: Optional end datetime

        Returns:
            Dictionary with ingestion result:
            {
                "success": bool,
                "data": Any,  # Adapter-specific format
                "vendor": str,
                "adapter_id": str,
                "ingested_at": str,
                "record_count": int,
                "error": str (if failed)
            }
        """
        operation_id = uuid.uuid4().hex[:8]
        start_time = datetime.utcnow()

        log_event(
            stage="ingestion",
            block=self.adapter_id,
            level="INFO",
            msg=f"Starting ingestion for {symbol}",
            extra={
                "operation_id": operation_id,
                "symbol": symbol,
                "start": start.isoformat() if start else None,
                "end": end.isoformat() if end else None,
            },
        )

        try:
            result = await self._execute_ingest_internal(symbol, start=start, end=end)
            duration_ms = (datetime.utcnow() - start_time).total_seconds() * 1000

            log_event(
                stage="ingestion",
                block=self.adapter_id,
                level="INFO",
                msg=f"Completed ingestion for {symbol}",
                extra={
                    "operation_id": operation_id,
                    "symbol": symbol,
                    "duration_ms": round(duration_ms, 2),
                    "success": result.get("success", False),
                    "record_count": result.get("record_count", 0),
                },
            )

            return result

        except Exception as e:
            duration_ms = (datetime.utcnow() - start_time).total_seconds() * 1000

            log_event(
                stage="ingestion",
                block=self.adapter_id,
                level="ERROR",
                msg=f"Ingestion failed for {symbol}: {str(e)}",
                extra={
                    "operation_id": operation_id,
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

    @abstractmethod
    async def _execute_ingest_internal(
        self,
        symbol: str,
        start: Optional[datetime] = None,
        end: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        """
        Internal ingestion logic - implement in subclass

        Args:
            symbol: Asset symbol to ingest
            start: Optional start datetime
            end: Optional end datetime

        Returns:
            Dictionary with ingestion result
        """
        pass