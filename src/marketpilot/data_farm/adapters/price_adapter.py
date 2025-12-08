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
    """Price data adapter with offset-based pagination"""

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)

        self.api_base_url = os.getenv("PRICE_API_BASE_URL")
        if not self.api_base_url:
            raise ValueError("PRICE_API_BASE_URL not found in environment")
        
        # Lock per symbol to prevent concurrent fetches
        self._fetch_locks: Dict[str, asyncio.Lock] = {}

        # Pagination configuration
        self.default_limit = config.get("limit", 1000)
        self.enable_pagination = config.get("enable_pagination", True)
        self.max_pages = config.get("max_pages", 100)
        self.max_total_records = config.get("max_total_records", 100000)
        self.page_delay = config.get("page_delay", 0.3)

        # Retry handler with centralized validation
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
            msg="Price adapter initialized with self-calculated offset",
            extra={
                "base_url": self.api_base_url,
                "limit": self.default_limit,
                "pagination_enabled": self.enable_pagination,
                "max_pages": self.max_pages,
            },
        )

    def _build_api_url(
        self,
        symbol: str,
        start: Optional[datetime],
        end: Optional[datetime],
        limit: int = 1000,
        offset: int = 0,
    ) -> str:
        """Build API URL with offset pagination"""
        if start is None or end is None:
            end = datetime.utcnow()
            start = end - timedelta(minutes=1)

        params = {
            "symbol": symbol,
            "start": start.strftime("%Y%m%d-%H%M"),
            "end": end.strftime("%Y%m%d-%H%M"),
            "limit": limit,
            "offset": offset,
        }
        
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

    def _should_continue_pagination(
        self,
        api_response: Dict[str, Any],
        records_count: int,
        current_offset: int,
        total_fetched: int,
    ) -> bool:
        """
        Determine if pagination should continue based on:
        1. API metadata (if available)
        2. Number of records returned
        3. Total vs offset position
        """
        # Safely get pagination metadata
        pagination = api_response.get("pagination") or api_response.get("metadata") or {}
        
        # Check explicit has_more flag
        if "has_more" in pagination:
            has_more = pagination["has_more"]
            log_event(
                stage="ingestion",
                block=self.adapter_id,
                level="DEBUG",
                msg=f"API says has_more={has_more}",
            )
            return has_more
        
        # Check has_next flag
        if "has_next" in pagination:
            has_next = pagination["has_next"]
            log_event(
                stage="ingestion",
                block=self.adapter_id,
                level="DEBUG",
                msg=f"API says has_next={has_next}",
            )
            return has_next
        
        # Check total count
        total = pagination.get("total", 0)
        if total > 0:
            has_more = (current_offset + records_count) < total
            log_event(
                stage="ingestion",
                block=self.adapter_id,
                level="DEBUG",
                msg=f"Checking total: {current_offset + records_count} < {total} = {has_more}",
            )
            return has_more
        
        # If no records returned, stop pagination
        if records_count == 0:
            log_event(
                stage="ingestion",
                block=self.adapter_id,
                level="INFO",
                msg="No records in page - end of data",
            )
            return False
        
        # Check if partial page (less than limit)
        limit = pagination.get("limit", self.default_limit)
        if records_count < limit:
            log_event(
                stage="ingestion",
                block=self.adapter_id,
                level="INFO",
                msg=f"Partial page received ({records_count} < {limit}) - end of data",
            )
            return False

        # Full page received, assume more data exists
        log_event(
            stage="ingestion",
            block=self.adapter_id,
            level="INFO",
            msg=f"Full page received ({records_count} = {limit}) - continuing",
        )
        return True

    async def _fetch_all_pages(
        self,
        symbol: str,
        start: datetime,
        end: datetime,
    ) -> Dict[str, Any]:
        """Fetch all pages with self-calculated offset"""
        all_records = []
        current_offset = 0  
        page_count = 0
        total_fetched = 0
        
        pagination_stats = {
            "total_pages_fetched": 0,
            "total_records": 0,
            "truncated": False,
            "truncation_reason": None,
            "pagination_method": "self_calculated_offset",
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
                    extra={"symbol": symbol, "records_fetched": total_fetched},
                )
                pagination_stats["truncated"] = True
                pagination_stats["truncation_reason"] = f"max_pages_{self.max_pages}"
                break

            if total_fetched >= self.max_total_records:
                log_event(
                    stage="ingestion",
                    block=self.adapter_id,
                    level="WARNING",
                    msg=f"Reached max_total_records limit ({self.max_total_records})",
                    extra={"symbol": symbol, "records_fetched": total_fetched},
                )
                pagination_stats["truncated"] = True
                pagination_stats["truncation_reason"] = f"max_records_{self.max_total_records}"
                break

            url = self._build_api_url(
                symbol=symbol,
                start=start,
                end=end,
                limit=self.default_limit,
                offset=current_offset,
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
                    "offset": current_offset,
                    "limit": self.default_limit,
                    "total_so_far": total_fetched,
                    "url": url,
                },
            )

            # Rate limiting
            if page_count > 1 and self.page_delay > 0:
                await asyncio.sleep(self.page_delay)

            # Fetch with retry handler (automatic validation)
            status_code, api_response = await self.retry_handler.fetch_with_retry(
                url=url, symbol=symbol, method="GET", validate=True
            )

            # Handle errors (validation already done by retry_handler)
            if status_code != 200 or api_response is None:
                error_msg = f"API returned status {status_code}" if status_code > 0 else "Request failed"
                log_event(
                    stage="ingestion",
                    block=self.adapter_id,
                    level="ERROR",
                    msg=f"Failed at page {page_count}: {error_msg}",
                    extra={"status": status_code, "page": page_count, "symbol": symbol},
                )
                
                # On first page failure, return error immediately
                if page_count == 1:
                    return {"error": error_msg, "status_code": status_code}
                
                # On later pages, stop pagination but keep what we have
                pagination_stats["truncated"] = True
                pagination_stats["truncation_reason"] = f"error_page_{page_count}"
                break

            # Extract data (guaranteed to have 'data' field due to validation)
            page_data = api_response.get("data", [])
            page_records = len(page_data)
            
            # Empty data is valid - it means no more results
            if page_records == 0:
                if page_count == 1:
                    log_event(
                        stage="ingestion",
                        block=self.adapter_id,
                        level="INFO",
                        msg="No price data found for this time range",
                        extra={
                            "symbol": symbol,
                            "time_range": f"{start.isoformat()} to {end.isoformat()}",
                        },
                    )
                else:
                    log_event(
                        stage="ingestion",
                        block=self.adapter_id,
                        level="INFO",
                        msg="Empty page received - end of data",
                        extra={"page": page_count, "total_fetched": total_fetched},
                    )
                break
            
            # Append data
            all_records.extend(page_data)
            total_fetched += page_records
            
            log_event(
                stage="ingestion",
                block=self.adapter_id,
                level="INFO",
                msg=f"Page {page_count}: {page_records} records (total: {total_fetched:,})",
                extra={
                    "symbol": symbol,
                    "page": page_count,
                    "records_in_page": page_records,
                    "total_so_far": total_fetched,
                    "current_offset": current_offset,
                },
            )

            # Check if we should continue
            should_continue = self._should_continue_pagination(
                api_response,
                page_records,
                current_offset,
                total_fetched,
            )
            
            if not should_continue:
                log_event(
                    stage="ingestion",
                    block=self.adapter_id,
                    level="INFO",
                    msg="Reached end of data",
                    extra={
                        "symbol": symbol,
                        "total_pages": page_count,
                        "total_records": total_fetched,
                    },
                )
                break
            
            # Calculate next offset
            current_offset += page_records
            
            log_event(
                stage="ingestion",
                block=self.adapter_id,
                level="DEBUG",
                msg=f"Next offset calculated: {current_offset}",
                extra={
                    "previous_offset": current_offset - page_records,
                    "records_added": page_records,
                    "next_offset": current_offset,
                },
            )

        # Final stats
        pagination_stats["total_pages_fetched"] = page_count
        pagination_stats["total_records"] = total_fetched
        pagination_stats["avg_records_per_page"] = (
            round(total_fetched / page_count, 2) if page_count > 0 else 0
        )

        log_event(
            stage="ingestion",
            block=self.adapter_id,
            level="INFO",
            msg=f"Pagination complete: {total_fetched:,} records in {page_count} pages",
            extra=pagination_stats,
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
        if symbol not in self._fetch_locks:
            self._fetch_locks[symbol] = asyncio.Lock()
        
        async with self._fetch_locks[symbol]:
            return await self._execute_ingest_locked(symbol, start, end)
    
    async def _execute_ingest_locked(
        self,
        symbol: str,
        start: Optional[datetime] = None,
        end: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        """Internal method with lock protection"""
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

            if self.enable_pagination:
                fetch_result = await self._fetch_all_pages(symbol, start, end)
            else:
                url = self._build_api_url(symbol, start, end, self.default_limit, 0)
                status_code, api_response = await self.retry_handler.fetch_with_retry(
                    url=url, symbol=symbol, method="GET", validate=True
                )
                
                if status_code != 200 or not api_response:
                    return {
                        "success": False,
                        "error": f"API returned status {status_code}",
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

            if "error" in fetch_result:
                return {
                    "success": False,
                    "error": fetch_result["error"],
                    "vendor": self.vendor,
                    "adapter_id": self.adapter_id,
                }

            data_records = fetch_result["records"]
            pagination_stats = fetch_result["pagination_stats"]

            # Empty results are success, not error
            if not data_records:
                log_event(
                    stage="ingestion",
                    block=self.adapter_id,
                    level="INFO",
                    msg=f"No price data found for {symbol} in specified time range",
                    extra={
                        "symbol": symbol,
                        "time_range": f"{start.isoformat() if start else 'N/A'} to {end.isoformat() if end else 'N/A'}",
                    },
                )
                return {
                    "success": True,
                    "data": [],
                    "vendor": self.vendor,
                    "adapter_id": self.adapter_id,
                    "record_count": 0,
                    "metadata": {"pagination": pagination_stats},
                }

            transformed_data = self._transform_response(data_records, symbol)
            record_count = len(transformed_data)

            log_event(
                stage="ingestion",
                block=self.adapter_id,
                level="INFO",
                msg=f"Successfully ingested {record_count:,} records in {pagination_stats['total_pages_fetched']} pages",
                extra={
                    "symbol": symbol,
                    "record_count": record_count,
                    "pages": pagination_stats["total_pages_fetched"],
                    "avg_per_page": pagination_stats.get("avg_records_per_page", 0),
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
                extra={"symbol": symbol, "error_type": type(e).__name__},
            )
            return {
                "success": False,
                "error": error_msg,
                "vendor": self.vendor,
                "adapter_id": self.adapter_id,
            }