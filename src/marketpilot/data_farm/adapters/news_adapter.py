"""
Resilient News Adapter
"""

from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
import asyncio
import os
from urllib.parse import urlencode
from marketpilot.data_farm.adapters.base_adapter import BaseAdapter
from marketpilot.utils.logger import log_event
from marketpilot.data_farm.utils.symbol_mapper import map_symbol_to_slug
from marketpilot.data_farm.utils.api_retry_handler import create_retry_handler


class ResilientNewsAdapter(BaseAdapter):
    """News data adapter"""

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)

        self.api_base_url = os.getenv("NEWS_API_BASE_URL")
        if not self.api_base_url:
            raise ValueError("NEWS_API_BASE_URL not found in environment")
        
        # Lock per symbol to prevent concurrent fetches
        self._fetch_locks: Dict[str, asyncio.Lock] = {}

        self.default_limit = config.get("limit", 100)
        
        # Pagination configuration
        self.enable_pagination = config.get("enable_pagination", True)
        self.max_pages = config.get("max_pages", 10)
        self.max_total_records = config.get("max_total_records", 1000)
        self.page_delay = config.get("page_delay", 0.5)

        # Retry handler
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
            msg="News adapter initialized with pagination support",
            extra={
                "base_url": self.api_base_url,
                "limit": self.default_limit,
                "pagination_enabled": self.enable_pagination,
                "max_pages": self.max_pages,
                "max_total_records": self.max_total_records,
                "page_delay": self.page_delay,
            },
        )

    def _build_api_url(
        self,
        asset_slug: str,
        start: Optional[datetime],
        end: Optional[datetime],
        limit: int = 100,
        cursor: Optional[str] = None,
    ) -> str:
        """Build API URL with cursor-based pagination"""
        if start is None or end is None:
            end = datetime.utcnow()
            start = end - timedelta(days=1)

        params = {
            "asset_slug": asset_slug,
            "start": start.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "end": end.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "limit": limit,
            "sort_by": "releasedAt",
            "order": "desc",
        }
        
        if cursor:
            params["cursor"] = cursor
        
        return f"{self.api_base_url}?{urlencode(params)}"

    def _transform_response(
        self, articles: List[Dict], symbol: str, start: datetime, end: datetime
    ) -> Dict[str, Any]:
        """
        Transform API response to news schema format.
        
        API format example:
        [
            {
                "slug": "article-123",
                "title": "Breaking News",
                "subtitle": "Details here",
                "releasedAt": "2025-01-15T10:00:00Z",
                "source": "Reuters",
                "sourceName": "Reuters",
                "sourceUrl": "https://...",
                "assets": [{"symbol": "BINANCE:BTCUSDT.P", "name": "Bitcoin"}]
            }
        ]
        """
        transformed_items = []
        most_recent_time = None

        for article in articles:
            assets = article.get("assets", [])
            primary_symbol = assets[0].get("symbol") if assets else symbol

            releasedAt = article.get("releasedAt") 

            transformed_items.append({
                "news_id": article.get("slug", ""),
                "symbol": symbol,
                "primary_symbol": primary_symbol,
                "releasedAt": releasedAt,
                "title": article.get("title", ""),
                "subtitle": article.get("subtitle", ""),
                "source": article.get("source", ""),
                "source_name": article.get("sourceName", ""),
                "source_url": article.get("sourceUrl", ""),
                "assets": assets,
                "asset_count": len(assets),
                "mapping_confidence": 1.0 if assets else 0.5,
            })

        wrapper_timestamp = (
            most_recent_time.isoformat() 
            if most_recent_time 
            else datetime.utcnow().isoformat()
        )

        return {
            "symbol": symbol,
            "startdate": start.isoformat(),
            "enddate": end.isoformat(),
            "timestamp": wrapper_timestamp,
            "data": transformed_items,
        }

    async def _fetch_all_pages(
        self,
        asset_slug: str,
        symbol: str,
        start: datetime,
        end: datetime,
    ) -> Dict[str, Any]:
        """Fetch all pages of news data with cursor-based pagination"""
        all_articles = []
        current_cursor = None
        page_count = 0
        total_fetched = 0
        
        pagination_stats = {
            "total_pages_fetched": 0,
            "total_records": 0,
            "truncated": False,
            "truncation_reason": None,
            "last_cursor": None,
        }

        while True:
            page_count += 1
            
            # Page limit check
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

            # Record limit check
            if total_fetched >= self.max_total_records:
                log_event(
                    stage="ingestion",
                    block=self.adapter_id,
                    level="WARNING",
                    msg=f"Reached max_total_records limit ({self.max_total_records})",
                    extra={
                        "symbol": symbol,
                        "records_fetched": total_fetched,
                        "pages_fetched": page_count - 1,
                    },
                )
                pagination_stats["truncated"] = True
                pagination_stats["truncation_reason"] = f"max_records_limit_{self.max_total_records}"
                break

            # Build URL using cursor
            url = self._build_api_url(
                asset_slug, start, end, self.default_limit, current_cursor
            )
            print("--------news url")
            print(url)
            log_event(
                stage="ingestion",
                block=self.adapter_id,
                level="DEBUG",
                msg=f"Fetching page {page_count}",
                extra={
                    "symbol": symbol,
                    "page": page_count,
                    "cursor": current_cursor[:30] + "..." if current_cursor else None,
                    "total_so_far": total_fetched,
                },
            )

            # Apply delay for rate limiting
            if page_count > 1 and self.page_delay > 0:
                await asyncio.sleep(self.page_delay)

            # Fetch with retry handler
            status_code, api_response = await self.retry_handler.fetch_with_retry(
                url=url, symbol=symbol, method="GET"
            )

            # HTTP error
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
                    extra={"status": status_code, "page": page_count, "symbol": symbol},
                )
                
                if page_count == 1:
                    return {"error": error_msg, "status_code": status_code}
                
                pagination_stats["truncated"] = True
                pagination_stats["truncation_reason"] = f"error_at_page_{page_count}"
                break

            # API success flag check
            if not api_response.get("success", False):
                log_event(
                    stage="ingestion",
                    block=self.adapter_id,
                    level="ERROR",
                    msg=f"API returned success=false at page {page_count}",
                    extra={"page": page_count, "symbol": symbol},
                )
                if page_count == 1:
                    return {"error": "API returned success=false"}
                else:
                    pagination_stats["truncated"] = True
                    pagination_stats["truncation_reason"] = f"api_error_at_page_{page_count}"
                    break

            # Extract data
            page_data = api_response.get("data", [])
            pagination = api_response.get("pagination", {})
            
            all_articles.extend(page_data)
            total_fetched += len(page_data)
            
            log_event(
                stage="ingestion",
                block=self.adapter_id,
                level="INFO",
                msg=f"Page {page_count} fetched successfully",
                extra={
                    "symbol": symbol,
                    "page": page_count,
                    "articles_in_page": len(page_data),
                    "returned_in_page": pagination.get("returned", len(page_data)),
                    "total_so_far": total_fetched,
                    "has_next": pagination.get("has_next", False),
                },
            )

            has_next = pagination.get("has_next", False)
            next_cursor = pagination.get("next_cursor")
            pagination_stats["last_cursor"] = next_cursor
            
            if not has_next:
                log_event(
                    stage="ingestion",
                    block=self.adapter_id,
                    level="INFO",
                    msg="Reached end of pagination (has_next=false)",
                    extra={
                        "symbol": symbol,
                        "total_pages": page_count,
                        "total_records": total_fetched,
                    },
                )
                break
            
            if not next_cursor:
                log_event(
                    stage="ingestion",
                    block=self.adapter_id,
                    level="WARNING",
                    msg="has_next=true but next_cursor is missing",
                    extra={"symbol": symbol, "page": page_count, "pagination": pagination},
                )
                pagination_stats["truncated"] = True
                pagination_stats["truncation_reason"] = "missing_next_cursor"
                break
            
            current_cursor = next_cursor

        pagination_stats["total_pages_fetched"] = page_count
        pagination_stats["total_records"] = total_fetched

        return {
            "articles": all_articles,
            "pagination_stats": pagination_stats,
        }

    async def _execute_ingest_internal(
        self,
        symbol: str,
        start: Optional[datetime] = None,
        end: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        """Execute news data ingestion with pagination support"""
        # Prevent concurrent fetches for same symbol
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
            if start is None:
                start = self.config.get("start")
            if end is None:
                end = self.config.get("end")
            
            if start is None or end is None:
                end = datetime.utcnow()
                start = end - timedelta(days=1)

            asset_slug = map_symbol_to_slug(symbol)

            log_event(
                stage="ingestion",
                block=self.adapter_id,
                level="INFO",
                msg="Starting news ingestion",
                extra={
                    "symbol": symbol,
                    "asset_slug": asset_slug,
                    "time_range": f"{start.isoformat()} to {end.isoformat()}",
                    "pagination_enabled": self.enable_pagination,
                },
            )

            if self.enable_pagination:
                fetch_result = await self._fetch_all_pages(asset_slug, symbol, start, end)
            else:
                url = self._build_api_url(asset_slug, start, end, self.default_limit)
                print("-------news url")
                print(url)
                status_code, api_response = await self.retry_handler.fetch_with_retry(
                    url=url, symbol=symbol, method="GET"
                )
                
                # Handle failure
                if status_code != 200 or not api_response:
                    return {
                        "success": False,
                        "error": f"API returned status {status_code}",
                        "vendor": self.vendor,
                        "adapter_id": self.adapter_id,
                    }
                
                # Check API success flag                
                if not api_response.get("success", False):
                    return {
                        "success": False,
                        "error": "API returned success=false",
                        "vendor": self.vendor,
                        "adapter_id": self.adapter_id,
                    }
                
                page_data = api_response.get("data", [])
                pagination = api_response.get("pagination", {})
                
                fetch_result = {
                    "articles": page_data,
                    "pagination_stats": {
                        "total_pages_fetched": 1,
                        "total_records": len(page_data),
                        "truncated": pagination.get("has_next", False),
                        "truncation_reason": "pagination_disabled" if pagination.get("has_next") else None,
                    }
                }

            if "error" in fetch_result:
                return {
                    "success": False,
                    "error": fetch_result["error"],
                    "vendor": self.vendor,
                    "adapter_id": self.adapter_id,
                }

            news_data = fetch_result["articles"]
            pagination_stats = fetch_result["pagination_stats"]

            if not news_data:
                log_event(
                    stage=self.stage_name,
                    block=self.adapter_id,
                    level="WARNING",
                    msg=f"No news data for {symbol}",
                    extra={"asset_slug": asset_slug},
                )
                empty_result = {
                    "symbol": symbol,
                    "startdate": start.isoformat(),
                    "enddate": end.isoformat(),
                    "timestamp": datetime.utcnow().isoformat(),
                    "data": [],
                }
                return {
                    "success": True,
                    "data": empty_result,
                    "vendor": self.vendor,
                    "adapter_id": self.adapter_id,
                    "record_count": 0,
                    "metadata": {
                        "pagination": pagination_stats,
                        "asset_slug": asset_slug,
                    },
                }

            transformed_data = self._transform_response(news_data, symbol, start, end)
            record_count = len(news_data)

            log_event(
                stage="ingestion",
                block=self.adapter_id,
                level="INFO",
                msg=f"Successfully ingested {record_count} news articles",
                extra={
                    "symbol": symbol,
                    "record_count": record_count,
                    "pages_fetched": pagination_stats["total_pages_fetched"],
                    "truncated": pagination_stats.get("truncated", False),
                    "truncation_reason": pagination_stats.get("truncation_reason"),
                    "time_range": {"start": start.isoformat(), "end": end.isoformat()},
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
                    "asset_slug": asset_slug,
                    "time_range": {
                        "start": start.isoformat(),
                        "end": end.isoformat()
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
                    "error_details": str(e),
                },
            )
            return {
                "success": False,
                "error": error_msg,
                "vendor": self.vendor,
                "adapter_id": self.adapter_id,
            }