"""
Resilient Price Adapter
"""

from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
import asyncio
import os
from urllib.parse import urlencode
from marketpilot.data_farm.adapters.base_adapter import BaseAdapter
from marketpilot.utils.logger import log_event
from marketpilot.data_farm.utils.api_retry_handler import create_retry_handler


class ResilientPriceAdapter(BaseAdapter):
    """Price data adapter"""

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)

        self.api_base_url = os.getenv("PRICE_API_BASE_URL")
        if not self.api_base_url:
            raise ValueError("PRICE_API_BASE_URL not found in environment")

        # Pagination configuration
        self.default_limit = config.get("limit", 1000)
        self.enable_pagination = config.get("enable_pagination", True)
        self.max_pages = config.get("max_pages", 100)  
        self.max_total_records = config.get("max_total_records", 100000)  
        self.page_delay = config.get("page_delay", 0.3)  

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
            msg="Price adapter initialized with pagination support",
            extra={
                "base_url": self.api_base_url,
                "limit": self.default_limit,
                "pagination_enabled": self.enable_pagination,
                "max_pages": self.max_pages,
                "max_total_records": self.max_total_records,
            },
        )

    def _build_api_url(
        self,
        symbol: str,
        start: Optional[datetime],
        end: Optional[datetime],
        limit: int = 1000,
        offset: Optional[int] = None,
        cursor: Optional[str] = None,
    ) -> str:
        """
        Build API URL with pagination parameters
        
        Supports both offset-based and cursor-based pagination:
        - offset: Traditional pagination (page 1 = offset 0, page 2 = offset 1000)
        - cursor: Cursor-based pagination (like news API)
        """
        if start is None or end is None:
            end = datetime.utcnow()
            start = end - timedelta(minutes=1)

        params = {
            "symbol": symbol,
            "start": start.strftime("%Y%m%d-%H%M"),
            "end": end.strftime("%Y%m%d-%H%M"),
            "limit": limit,
        }
        
        # Pagination parameter
        if cursor:
            params["cursor"] = cursor
        elif offset is not None and offset > 0:
            params["offset"] = offset
        
        return f"{self.api_base_url}?{urlencode(params)}"

    def _transform_response(
        self, 
        api_records: List[Dict], 
        symbol: str
    ) -> List[Dict[str, Any]]:
        """
        Transform API response to price schema format
        
        API format:
        [
            {
                "symbol": "BINANCE:BTCUSDT.P",
                "candle_time": "2025-01-15T10:00:00Z",
                "open": 95000.5,
                "high": 95500.0,
                "low": 94800.0,
                "close": 95200.0,
                "volume": 1234.56
            },
            ...
        ]
        """
        transformed = []
        
        for record in api_records:
            candle_time = record.get("candle_time")
            
            transformed.append({
                "symbol": symbol,
                "candle_time": candle_time,
                "open": float(record.get("open", 0)),
                "high": float(record.get("high", 0)),
                "low": float(record.get("low", 0)),
                "close": float(record.get("close", 0)),
                "volume": float(record.get("volume", 0)),
            })
        
        return transformed

    async def _fetch_all_pages(
        self,
        symbol: str,
        start: datetime,
        end: datetime,
    ) -> Dict[str, Any]:
        """
        Fetch all pages of price data with pagination
        
        Supports both pagination methods:
        1. Cursor-based (if API returns next_cursor)
        2. Offset-based (fallback if no cursor support)
        
        Returns:
            Dict with combined records and pagination stats
        """
        all_records = []
        current_cursor = None
        current_offset = 0
        page_count = 0
        total_fetched = 0
        
        pagination_stats = {
            "total_pages_fetched": 0,
            "total_records": 0,
            "truncated": False,
            "truncation_reason": None,
            "pagination_method": "unknown",  # cursor or offset
        }

        while True:
            page_count += 1
            
            # Check limits
            if page_count > self.max_pages:
                log_event(
                    stage="ingestion",
                    block=self.adapter_id,
                    level="WARNING",
                    msg=f"Reached max_pages limit ({self.max_pages})",
                    extra={
                        "symbol": symbol,
                        "records_fetched": total_fetched,
                        "pages_fetched": page_count - 1,
                    },
                )
                pagination_stats["truncated"] = True
                pagination_stats["truncation_reason"] = f"max_pages_limit_{self.max_pages}"
                break

            if total_fetched >= self.max_total_records:
                log_event(
                    stage="ingestion",
                    block=self.adapter_id,
                    level="WARNING",
                    msg=f"Reached max_total_records limit ({self.max_total_records})",
                    extra={
                        "symbol": symbol,
                        "records_fetched": total_fetched,
                    },
                )
                pagination_stats["truncated"] = True
                pagination_stats["truncation_reason"] = f"max_records_limit_{self.max_total_records}"
                break

            # Build URL
            url = self._build_api_url(
                symbol, start, end, 
                self.default_limit, 
                current_offset,
                current_cursor
            )
            print("-------price url")
            print(url)
            
            log_event(
                stage="ingestion",
                block=self.adapter_id,
                level="DEBUG",
                msg=f"Fetching page {page_count}",
                extra={
                    "symbol": symbol,
                    "page": page_count,
                    "offset": current_offset if not current_cursor else None,
                    "cursor": current_cursor[:30] + "..." if current_cursor else None,
                    "total_so_far": total_fetched,
                },
            )

            # Rate limiting
            if page_count > 1 and self.page_delay > 0:
                await asyncio.sleep(self.page_delay)

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
                log_event(
                    stage="ingestion",
                    block=self.adapter_id,
                    level="ERROR",
                    msg=f"Failed at page {page_count}: {error_msg}",
                    extra={"status": status_code, "page": page_count},
                )
                
                if page_count == 1:
                    return {"error": error_msg, "status_code": status_code}
                else:
                    pagination_stats["truncated"] = True
                    pagination_stats["truncation_reason"] = f"error_at_page_{page_count}"
                    break

            # Check API success
            if not api_response.get("success", False):
                error_msg = api_response.get("error", "API returned success=false")
                if page_count == 1:
                    return {"error": error_msg}
                else:
                    pagination_stats["truncated"] = True
                    pagination_stats["truncation_reason"] = "api_error"
                    break

            # Extract data
            page_data = api_response.get("data", [])
            pagination = api_response.get("pagination", {})
            
            # Append data
            all_records.extend(page_data)
            page_records = len(page_data)
            total_fetched += page_records
            
            # Detect pagination type
            has_next_cursor = pagination.get("has_next", False) and pagination.get("next_cursor")
            has_more_data = page_records >= self.default_limit
            
            if has_next_cursor:
                pagination_stats["pagination_method"] = "cursor"
            elif pagination_stats["pagination_method"] == "unknown":
                pagination_stats["pagination_method"] = "offset"
            
            log_event(
                stage="ingestion",
                block=self.adapter_id,
                level="INFO",
                msg=f"Page {page_count} fetched: {page_records} records (total: {total_fetched})",
                extra={
                    "symbol": symbol,
                    "page": page_count,
                    "records_in_page": page_records,
                    "total_so_far": total_fetched,
                    "pagination_method": pagination_stats["pagination_method"],
                },
            )

            # Check if pagination continues
            if has_next_cursor:
                # Cursor-based pagination
                current_cursor = pagination.get("next_cursor")
            elif has_more_data:
                # Offset-based pagination
                current_offset += self.default_limit
            else:
                # No more data
                log_event(
                    stage="ingestion",
                    block=self.adapter_id,
                    level="INFO",
                    msg=f"Reached end of data (received {page_records} < {self.default_limit})",
                    extra={
                        "symbol": symbol,
                        "total_pages": page_count,
                        "total_records": total_fetched,
                    },
                )
                break

        # Final stats
        pagination_stats["total_pages_fetched"] = page_count
        pagination_stats["total_records"] = total_fetched
        pagination_stats["avg_records_per_page"] = (
            round(total_fetched / page_count, 2) if page_count > 0 else 0
        )

        return {
            "records": all_records,
            "pagination_stats": pagination_stats,
        }

    async def _execute_ingest_internal(
        self,
        symbol: str,
        start: Optional[datetime] = None,
        end: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        """Execute price data ingestion with pagination support"""
        try:
            log_event(
                stage="ingestion",
                block=self.adapter_id,
                level="INFO",
                msg="Starting price ingestion",
                extra={
                    "symbol": symbol,
                    "start": start.isoformat() if start else None,
                    "end": end.isoformat() if end else None,
                    "pagination_enabled": self.enable_pagination,
                },
            )

            # Fetch with or without pagination
            if self.enable_pagination:
                fetch_result = await self._fetch_all_pages(symbol, start, end)
            else:
                # Legacy method: single request
                url = self._build_api_url(symbol, start, end, self.default_limit)
                status_code, api_response = await self.retry_handler.fetch_with_retry(
                    url=url, symbol=symbol, method="GET"
                )
                
                if status_code != 200 or not api_response:
                    return {
                        "success": False,
                        "error": f"API returned status {status_code}",
                        "vendor": self.vendor,
                        "adapter_id": self.adapter_id,
                    }
                
                if not api_response.get("success", False):
                    return {
                        "success": False,
                        "error": api_response.get("error", "API returned success=false"),
                        "vendor": self.vendor,
                        "adapter_id": self.adapter_id,
                    }
                
                page_data = api_response.get("data", [])
                
                fetch_result = {
                    "records": page_data,
                    "pagination_stats": {
                        "total_pages_fetched": 1,
                        "total_records": len(page_data),
                        "truncated": False,
                        "pagination_method": "disabled",
                    }
                }

            # Check for errors
            if "error" in fetch_result:
                return {
                    "success": False,
                    "error": fetch_result["error"],
                    "vendor": self.vendor,
                    "adapter_id": self.adapter_id,
                }

            data_records = fetch_result["records"]
            pagination_stats = fetch_result["pagination_stats"]

            # Handle no data case
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
                    "metadata": {
                        "pagination": pagination_stats,
                    },
                }

            # Transform response
            transformed_data = self._transform_response(data_records, symbol)
            record_count = len(transformed_data)

            log_event(
                stage="ingestion",
                block=self.adapter_id,
                level="INFO",
                msg=f"Successfully ingested {record_count} price records",
                extra={
                    "symbol": symbol,
                    "record_count": record_count,
                    "pages_fetched": pagination_stats["total_pages_fetched"],
                    "pagination_method": pagination_stats["pagination_method"],
                    "truncated": pagination_stats.get("truncated", False),
                },
            )

            return {
                "success": True,
                "data": transformed_data,
                "vendor": self.vendor,
                "adapter_id": self.adapter_id,
                "ingested_at": datetime.utcnow().isoformat(),
                "record_count": record_count,
                "metadata": {
                    "pagination": pagination_stats,
                    "time_range": {
                        "start": start.isoformat() if start else None,
                        "end": end.isoformat() if end else None,
                    },
                },
            }

        except Exception as e:
            error_msg = f"Unexpected error: {str(e)}"
            log_event(
                stage="ingestion",
                block=self.adapter_id,
                level="ERROR",
                msg=error_msg,
                extra={
                    "symbol": symbol,
                    "error_type": type(e).__name__,
                },
            )
            return {
                "success": False,
                "error": error_msg,
                "vendor": self.vendor,
                "adapter_id": self.adapter_id,
            }
