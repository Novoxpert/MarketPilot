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
    """News data adapter with retry mechanism"""

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
        """Transform API response to standard format"""
        transformed = []

        for article in articles:
            assets = article.get("assets", [])
            primary_symbol = assets[0].get("symbol") if assets else symbol

            transformed.append(
                {
                    "news_id": article.get("slug", ""),
                    "symbol": symbol,
                    "primary_symbol": primary_symbol,
                    "published_at_utc": article.get("releasedAt", ""),
                    "title": article.get("title", ""),
                    "subtitle": article.get("subtitle", ""),
                    "source": article.get("source", ""),
                    "source_name": article.get("sourceName", ""),
                    "source_url": article.get("sourceUrl", ""),
                    "assets": assets,
                    "asset_count": len(assets),
                    "mapping_confidence": 1.0 if assets else 0.5,
                }
            )

        return {
            "symbol": symbol,
            "startdate": start.isoformat(),
            "enddate": end.isoformat(),
            "timestamp": datetime.utcnow().isoformat(),
            "data": transformed,
        }

    async def _execute_ingest_internal(
        self,
        symbol: str,
        start: Optional[datetime] = None,
        end: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        """Execute news data ingestion"""
        try:
            # Map symbol to slug
            asset_slug = map_symbol_to_slug(symbol)

            if start is None or end is None:
                end = datetime.utcnow()
                start = end - timedelta(days=1)

            url = self._build_api_url(asset_slug, start, end, self.default_limit)

            log_event(
                stage="ingestion",
                block=self.adapter_id,
                level="DEBUG",
                msg="Fetching news data",
                extra={"symbol": symbol, "asset_slug": asset_slug},
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
                    stage="ingestion",
                    block=self.adapter_id,
                    level="WARNING",
                    msg=f"No news data for {symbol}",
                )
                empty_result = self._transform_response([], symbol, start, end)
                return {
                    "success": True,
                    "data": empty_result,
                    "vendor": self.vendor,
                    "adapter_id": self.adapter_id,
                    "record_count": 0,
                    "metadata": {"pagination": pagination, "asset_slug": asset_slug},
                }

            # Transform
            transformed_data = self._transform_response(news_data, symbol, start, end)
            record_count = len(news_data)

            log_event(
                stage="ingestion",
                block=self.adapter_id,
                level="INFO",
                msg=f"Successfully ingested {record_count} news articles",
                extra={"symbol": symbol, "record_count": record_count},
            )

            return {
                "success": True,
                "data": transformed_data,
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