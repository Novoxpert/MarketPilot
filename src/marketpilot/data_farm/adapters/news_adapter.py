"""
Resilient News Adapter 
"""

from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
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

        self.default_limit = config.get("limit", 100)

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
            msg="News adapter initialized",
            extra={"base_url": self.api_base_url, "limit": self.default_limit},
        )

    def _build_api_url(
        self,
        asset_slug: str,
        start: Optional[datetime],
        end: Optional[datetime],
        limit: int = 100,
    ) -> str:
        """Build API URL"""
        if start is None or end is None:
            end = datetime.utcnow()
            start = end - timedelta(days=1)

        params = {
            "asset_slug": asset_slug,
            "from_date": start.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "to_date": end.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "limit": limit,
            "sort_by": "releasedAt",
            "order": "desc",
        }
        return f"{self.api_base_url}?{urlencode(params)}"

    def _transform_response(
        self, articles: List[Dict], symbol: str, start: datetime, end: datetime
    ) -> Dict[str, Any]:
        """
        Transform API response to news schema format
        
        API format:
        [
            {
                "slug": "article-123",
                "title": "Breaking News",
                "subtitle": "Details here",
                "releasedAt": "2025-01-15T10:00:00Z",
                "source": "Reuters",
                "sourceName": "Reuters",
                "sourceUrl": "https://...",
                "assets": [
                    {"symbol": "BINANCE:BTCUSDT.P", "name": "Bitcoin"}
                ]
            },
            ...
        ]
        """
        transformed_items = []
        most_recent_time = None

        for article in articles:
            assets = article.get("assets", [])
            # Primary symbol is the first asset or the requested symbol
            primary_symbol = assets[0].get("symbol") if assets else symbol

            # Normalize timestamp field
            published_at = article.get("releasedAt") or article.get("published_at")
            
            # Track most recent article time for wrapper timestamp
            if published_at:
                article_time = datetime.fromisoformat(published_at.replace("Z", "+00:00"))
                if most_recent_time is None or article_time > most_recent_time:
                    most_recent_time = article_time
            # {
            # "slug": "bitcoin-drop-isnt-the-real-crisis-heres-what-the-market-fears",
            # "title": "Bitcoin Drop Isn’t the Real Crisis – Here’s What the Market Fears",
            # "subtitle": "Key Takeaways The real fear in the market is the possible removal of Bitcoin-heavy companies from MSCI indexes, not just […] The post Bitcoin Drop Isn’t the Real Crisis – Here’s What the Market Fears appeared first on Coindoo.",
            # "source": "coinmarketcap",
            # "sourceName": "Coindoo",
            # "sourceUrl": "https://coinmarketcap.com/community/en/articles/692f15261003e82d94599185",
            # "releasedAt": "2025-12-02T16:30:13",
            # "assets": [
            #     {
            #     "name": "Metaplanet",
            #     "slug": "metaplanet-ethereum",
            #     "symbol": "MTPLF"
            #     },
            #     {
            #     "name": "American Bitcoin",
            #     "slug": "american-bitcoin",
            #     "symbol": "ABTC"
            #     },
            #     {
            #     "name": "Bitcoin",
            #     "slug": "bitcoin",
            #     "symbol": "BTC"
            #     },
            #     {
            #     "name": "American Bitcoin",
            #     "slug": "american-bitcoin-solana",
            #     "symbol": "ABTC"
            #     },
            #     {
            #     "name": "Real",
            #     "slug": "realyn",
            #     "symbol": "REAL"
            #     }
            # ]
            # },
            transformed_items.append({
                "news_id": article.get("slug", ""),
                "symbol": symbol,  # Use requested symbol
                "primary_symbol": primary_symbol,
                "published_at_utc": published_at,
                "title": article.get("title", ""),
                "subtitle": article.get("subtitle", ""),
                "source": article.get("source", ""),
                "source_name": article.get("sourceName", ""),
                "source_url": article.get("sourceUrl", ""),
                "assets": assets,
                "asset_count": len(assets),
                "mapping_confidence": 1.0 if assets else 0.5,
            })

        # Use most recent article time as timestamp (not ingestion time)
        wrapper_timestamp = (
            most_recent_time.isoformat() 
            if most_recent_time 
            else datetime.utcnow().isoformat()
        )

        return {
            "symbol": symbol,
            "startdate": start.isoformat(),
            "enddate": end.isoformat(),
            "timestamp": wrapper_timestamp,  # Most recent article, not ingestion time
            "data": transformed_items,
        }

    async def _execute_ingest_internal(
        self,
        symbol: str,
        start: Optional[datetime] = None,
        end: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        """Execute news data ingestion with schema-compliant transformation"""
        try:
            # Use config start/end if provided (for time range override)
            if start is None:
                start = self.config.get("start")
            if end is None:
                end = self.config.get("end")
            
            # Default to last 24 hours if still None
            if start is None or end is None:
                end = datetime.utcnow()
                start = end - timedelta(days=1)

            # Map symbol to slug
            asset_slug = map_symbol_to_slug(symbol)

            url = self._build_api_url(asset_slug, start, end, self.default_limit)
            print("-------news url")
            print(url)
            log_event(
                stage="ingestion",
                block=self.adapter_id,
                level="DEBUG",
                msg="Fetching news data",
                extra={
                    "symbol": symbol, 
                    "asset_slug": asset_slug,
                    "start": start.isoformat(),
                    "end": end.isoformat(),
                },
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
                return {
                    "success": False,
                    "error": "API returned success=false",
                    "vendor": self.vendor,
                    "adapter_id": self.adapter_id,
                }

            # Extract data
            news_data = api_response.get("data", [])
            pagination = api_response.get("pagination", {})

            if not news_data:
                log_event(
                    stage=self.stage_name,
                    block=self.adapter_id,
                    level="WARNING",
                    msg=f"No news data for {symbol}",
                )
                # Return empty but successful result with schema structure
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
                    "metadata": {"pagination": pagination, "asset_slug": asset_slug},
                }

            # Transform response to schema format
            transformed_data = self._transform_response(news_data, symbol, start, end)
            record_count = len(news_data)

            log_event(
                stage="ingestion",
                block=self.adapter_id,
                level="INFO",
                msg=f"Successfully ingested and transformed {record_count} news articles",
                extra={
                    "symbol": symbol, 
                    "record_count": record_count,
                    "time_range": {
                        "start": start.isoformat(),
                        "end": end.isoformat(),
                    }
                },
            )

            return {
                "success": True,
                "data": transformed_data,  # ✅ Schema-compliant wrapper
                "vendor": self.vendor,
                "adapter_id": self.adapter_id,
                "ingested_at": datetime.utcnow().isoformat(),
                "record_count": record_count,
                "metadata": {
                    "pagination": pagination,
                    "asset_slug": asset_slug,
                    "time_range": {"start": start.isoformat(), "end": end.isoformat()},
                },
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