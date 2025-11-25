"""
Resilient Price Adapter using Internal OHLCV API
"""

from typing import Dict, Any, Optional
from datetime import datetime, timedelta
import os
import aiohttp
from urllib.parse import urlencode
from marketpilot.data_farm.adapters.base_adapter import BaseAdapter
from marketpilot.utils.logger import log_event


class ResilientPriceAdapter(BaseAdapter):
    """Price data adapter using internal OHLCV API"""

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)

        # Base URL from environment
        self.api_base_url = os.getenv("PRICE_API_BASE_URL")

        if not self.api_base_url:
            raise ValueError(
                "PRICE_API_BASE_URL not found. Please set it in your .env file."
            )

        log_event(
            stage="initialization",
            block="adapter",
            level="INFO",
            msg="Initialized ResilientPriceAdapter",
            extra={
                "adapter_id": self.adapter_id,
                "base_url": self.api_base_url,
            },
        )

    def _build_api_url(
        self,
        symbol: str,
        start: Optional[datetime],
        end: Optional[datetime],
    ) -> str:
        """Build API URL with proper timestamp handling"""
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
        """Execute ingestion with proper error handling"""

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
                    "start": start.isoformat() if start else None,
                    "end": end.isoformat() if end else None,
                },
            )

            async with aiohttp.ClientSession() as session:
                async with session.get(
                    url, timeout=aiohttp.ClientTimeout(total=30)
                ) as response:
                    if response.status != 200:
                        error_msg = f"API returned status {response.status}"
                        text = await response.text()
                        log_event(
                            stage="ingestion",
                            block="adapter",
                            level="ERROR",
                            msg=error_msg,
                            extra={"status": response.status, "response": text[:200]},
                        )
                        self.log_error(symbol, error_msg)
                        return {
                            "success": False,
                            "error": error_msg,
                            "vendor": self.vendor,
                            "status_code": response.status,
                        }

                    api_response = await response.json()
            print("api_response")
            print(api_response)
            # Check API response success flag
            if not api_response.get("success", False):
                error_msg = api_response.get("error", "API returned success=false")
                self.log_error(symbol, error_msg)
                return {"success": False, "error": error_msg, "vendor": self.vendor}

            data_records = api_response.get("data", [])
            metadata = api_response.get("metadata", {})

            if not data_records:
                log_event(
                    stage="ingestion",
                    block="adapter",
                    level="WARNING",
                    msg=f"No data returned for symbol {symbol}",
                    extra={"adapter_id": self.adapter_id, "symbol": symbol},
                )
                return {
                    "success": True,
                    "data": [],
                    "vendor": self.vendor,
                    "record_count": 0,
                    "metadata": metadata,
                }

            # Validate schema for first record
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
                    "mode": "latest" if (start is None or end is None) else "range",
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

        except aiohttp.ClientError as e:
            error_msg = f"Network error: {str(e)}"
            self.log_error(symbol, error_msg)
            return {"success": False, "error": error_msg, "vendor": self.vendor}

        except Exception as e:
            error_msg = f"Unexpected error: {str(e)}"
            self.log_error(symbol, error_msg)
            return {"success": False, "error": error_msg, "vendor": self.vendor}


# Example usage
if __name__ == "__main__":
    import asyncio

    config = {
        "vendor": "internal_api",
        "id": "price_internal_001",
        "cadence": "1min",
        "schema_type": "price",
    }

    adapter = ResilientPriceAdapter(config)

    print("\n=== Fetch latest candle ===")
    latest = asyncio.run(adapter.execute_ingest("BINANCE:BTCUSDT.P"))
    print(f"Success: {latest.get('success')}")
    print(f"Records: {latest.get('record_count', 0)}")

    print("\n=== Fetch last 10 minutes ===")
    end = datetime.utcnow()
    start = end - timedelta(minutes=10)
    last_10min = asyncio.run(
        adapter.execute_ingest("BINANCE:BTCUSDT.P", start=start, end=end)
    )
    print(f"Success: {last_10min.get('success')}")
    print(f"Records: {last_10min.get('record_count', 0)}")
