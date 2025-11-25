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
    """Price data adapter with shared retry mechanism"""

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)

        # API configuration
        self.api_base_url = os.getenv("PRICE_API_BASE_URL")
        if not self.api_base_url:
            raise ValueError("PRICE_API_BASE_URL not found in environment")

        # Initialize retry handler with config
        self.retry_handler = create_retry_handler(
            adapter_id=self.adapter_id,
            max_retries=config.get("max_retries", 3),
            retry_delay=config.get("retry_delay", 2.0),
            backoff_factor=config.get("backoff_factor", 2.0),
            timeout=config.get("timeout", 30),
        )

        log_event(
            stage="initialization",
            block="adapter",
            level="INFO",
            msg="Initialized ResilientPriceAdapter",
            extra={
                "adapter_id": self.adapter_id,
                "base_url": self.api_base_url,
                "max_retries": config.get("max_retries", 3),
            },
        )

    def _build_api_url(
        self,
        symbol: str,
        start: Optional[datetime],
        end: Optional[datetime],
    ) -> str:
        """Build API URL"""
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
        """Execute ingestion using shared retry handler"""

        try:
            url = self._build_api_url(symbol, start, end)
            print("url")
            print(url)
            log_event(
                stage="ingestion",
                block="adapter",
                level="DEBUG",
                msg="Fetching price data from API",
                extra={
                    "adapter_id": self.adapter_id,
                    "symbol": symbol,
                    "url": url,
                },
            )

            # Use shared retry handler
            status_code, api_response = await self.retry_handler.fetch_with_retry(
                url=url, symbol=symbol, method="GET"
            )

            # Check if request succeeded
            if status_code != 200 or api_response is None:
                error_msg = (
                    f"API returned status {status_code}"
                    if status_code > 0
                    else "Request failed after retries"
                )
                self.log_error(symbol, error_msg)
                return {
                    "success": False,
                    "error": error_msg,
                    "vendor": self.vendor,
                    "status_code": status_code,
                }


            print("api_response")
            print(api_response)
            # Check API success flag
            if not api_response.get("success", False):
                error_msg = api_response.get("error", "API returned success=false")
                self.log_error(symbol, error_msg)
                return {"success": False, "error": error_msg, "vendor": self.vendor}

            # Extract data
            data_records = api_response.get("data", [])
            metadata = api_response.get("metadata", {})

            if not data_records:
                log_event(
                    stage="ingestion",
                    block="adapter",
                    level="WARNING",
                    msg=f"No data returned for {symbol}",
                )
                return {
                    "success": True,
                    "data": [],
                    "vendor": self.vendor,
                    "record_count": 0,
                    "metadata": metadata,
                }

            # Validate schema
            if data_records:
                self.validate_schema(data_records[0])

            record_count = len(data_records)

            log_event(
                stage="ingestion",
                block="adapter",
                level="INFO",
                msg=f"Successfully ingested {record_count} records",
                extra={
                    "adapter_id": self.adapter_id,
                    "symbol": symbol,
                    "record_count": record_count,
                },
            )

            self.log_success(symbol, record_count=record_count)

            return {
                "success": True,
                "data": data_records,
                "vendor": self.vendor,
                "ingested_at": datetime.utcnow().isoformat(),
                "record_count": record_count,
                "metadata": metadata,
            }

        except Exception as e:
            error_msg = f"Unexpected error: {str(e)}"
            self.log_error(symbol, error_msg)
            return {"success": False, "error": error_msg, "vendor": self.vendor}