"""
Resilient Price Adapter
"""

from typing import Dict, Any, Optional
from datetime import datetime, timedelta
import os
from urllib.parse import urlencode
from marketpilot.data_farm.adapters.base_adapter import BaseAdapter
from marketpilot.utils.logger import log_event
from marketpilot.data_farm.utils.api_retry_handler import create_retry_handler


class ResilientPriceAdapter(BaseAdapter):
    """Price data adapter with retry mechanism"""

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)

        self.api_base_url = os.getenv("PRICE_API_BASE_URL")
        if not self.api_base_url:
            raise ValueError("PRICE_API_BASE_URL not found in environment")

        self.retry_handler = create_retry_handler(
            adapter_id=self.adapter_id,
            max_retries=config.get("max_retries", 3),
            retry_delay=config.get("retry_delay", 2.0),
            backoff_factor=config.get("backoff_factor", 2.0),
            timeout=config.get("timeout", 30),
        )

        log_event(
            stage="initialization",
            block=self.adapter_id,
            level="INFO",
            msg="Price adapter initialized",
            extra={"base_url": self.api_base_url},
        )

    def _build_api_url(
        self, symbol: str, start: Optional[datetime], end: Optional[datetime]
    ) -> str:
        """Build API URL with parameters"""
        if start is None or end is None:
            end = datetime.utcnow()
            start = end - timedelta(minutes=1)

        params = {
            "symbol": symbol,
            "start": start.strftime("%Y%m%d-%H%M"),
            "end": end.strftime("%Y%m%d-%H%M"),
        }
        return f"{self.api_base_url}?{urlencode(params)}"

    async def _execute_ingest_internal(
        self,
        symbol: str,
        start: Optional[datetime] = None,
        end: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        """Execute price data ingestion"""
        try:
            url = self._build_api_url(symbol, start, end)

            log_event(
                stage="ingestion",
                block=self.adapter_id,
                level="DEBUG",
                msg="Fetching price data",
                extra={"symbol": symbol, "url": url},
            )

            # Fetch with retry
            status_code, api_response = await self.retry_handler.fetch_with_retry(
                url=url, symbol=symbol, method="GET"
            )

            # Handle failure
            if status_code != 200 or api_response is None:
                error_msg = (
                    f"API returned status {status_code}"
                    if status_code > 0
                    else "Request failed after retries"
                )
                return {
                    "success": False,
                    "error": error_msg,
                    "vendor": self.vendor,
                    "adapter_id": self.adapter_id,
                }

            # Check API success flag
            if not api_response.get("success", False):
                error_msg = api_response.get("error", "API returned success=false")
                return {
                    "success": False,
                    "error": error_msg,
                    "vendor": self.vendor,
                    "adapter_id": self.adapter_id,
                }

            # Extract data
            data_records = api_response.get("data", [])
            metadata = api_response.get("metadata", {})

            if not data_records:
                log_event(
                    stage="ingestion",
                    block=self.adapter_id,
                    level="WARNING",
                    msg=f"No data returned for {symbol}",
                )
                return {
                    "success": True,
                    "data": [],
                    "vendor": self.vendor,
                    "adapter_id": self.adapter_id,
                    "record_count": 0,
                    "metadata": metadata,
                }

            record_count = len(data_records)

            log_event(
                stage="ingestion",
                block=self.adapter_id,
                level="INFO",
                msg=f"Successfully ingested {record_count} records",
                extra={"symbol": symbol, "record_count": record_count},
            )

            return {
                "success": True,
                "data": data_records,
                "vendor": self.vendor,
                "adapter_id": self.adapter_id,
                "ingested_at": datetime.utcnow().isoformat(),
                "record_count": record_count,
                "metadata": metadata,
            }

        except Exception as e:
            error_msg = f"Unexpected error: {str(e)}"
            log_event(
                stage="ingestion",
                block=self.adapter_id,
                level="ERROR",
                msg=error_msg,
                extra={"symbol": symbol},
            )
            return {
                "success": False,
                "error": error_msg,
                "vendor": self.vendor,
                "adapter_id": self.adapter_id,
            }