"""
Resilient News Adapter using Internal News API
"""

from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
import os
import aiohttp
from urllib.parse import urlencode
from marketpilot.data_farm.adapters.base_adapter import BaseAdapter
from marketpilot.utils.logger import log_event
from marketpilot.data_farm.utils.symbol_mapper import map_symbol_to_slug


class ResilientNewsAdapter(BaseAdapter):
    """News data adapter using internal News API"""

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)

        # Base URL from environment
        self.api_base_url = os.getenv("NEWS_API_BASE_URL")

        if not self.api_base_url:
            raise ValueError(
                "NEWS_API_BASE_URL not found. Please set it in your .env file."
            )

        # Default limit for news articles
        self.default_limit = config.get("limit", 100)

        log_event(
            stage="initialization",
            block="adapter",
            level="INFO",
            msg="Initialized ResilientNewsAdapter",
            extra={
                "adapter_id": self.adapter_id,
                "base_url": self.api_base_url,
                "default_limit": self.default_limit,
            },
        )

    def _map_symbol_to_asset_slug(self, symbol: str) -> str:
        """
        Map trading symbol to asset slug format expected by API
        Uses centralized symbol_mapper utility

        Args:
            symbol: Trading symbol (e.g., "BINANCE:BTCUSDT.P", "BTC", "AAPL")

        Returns:
            Asset slug (e.g., "bitcoin", "ethereum")
        """
        return map_symbol_to_slug(symbol)

    def _build_api_url(
        self,
        asset_slug: str,
        start: Optional[datetime],
        end: Optional[datetime],
        limit: int = 100,
    ) -> str:
        """Build API URL with proper parameters"""
        if start is None or end is None:
            end = datetime.utcnow()
            start = end - timedelta(days=1)  # Default: last 24 hours

        params = {
            "asset_slug": asset_slug,
            "from_date": start.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "to_date": end.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "limit": limit,
            "sort_by": "releasedAt",
            "order": "desc",
        }
        return f"{self.api_base_url}?{urlencode(params)}"

    def _transform_api_response(
        self,
        api_data: List[Dict[str, Any]],
        symbol: str,
        start: datetime,
        end: datetime,
    ) -> Dict[str, Any]:
        """
        Transform API response to match expected schema format

        Args:
            api_data: List of news articles from API
            symbol: Original symbol
            start: Start datetime
            end: End datetime

        Returns:
            Transformed data matching news schema
        """
        transformed_articles = []

        for article in api_data:
            # Extract assets and find primary asset
            assets = article.get("assets", [])
            primary_symbol = assets[0].get("symbol") if assets else symbol

            # Build transformed article
            transformed_article = {
                "news_id": article.get("slug", ""),
                "symbol": symbol,  # Keep original symbol
                "primary_symbol": primary_symbol,
                "published_at_utc": article.get("releasedAt", ""),
                "title": article.get("title", ""),
                "subtitle": article.get("subtitle", ""),
                "source": article.get("source", ""),
                "source_name": article.get("sourceName", ""),
                "source_url": article.get("sourceUrl", ""),
                "assets": assets,
                "asset_count": len(assets),
                "mapping_confidence": (
                    1.0 if assets else 0.5
                ),  # High confidence if assets present
            }

            transformed_articles.append(transformed_article)

        # Return in expected schema format
        return {
            "symbol": symbol,
            "startdate": start.isoformat(),
            "enddate": end.isoformat(),
            "timestamp": datetime.utcnow().isoformat(),
            "data": transformed_articles,
        }

    async def _execute_ingest_internal(
        self,
        symbol: str,
        start: Optional[datetime] = None,
        end: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        """Execute ingestion with proper error handling"""

        try:
            # Map symbol to asset slug
            asset_slug = self._map_symbol_to_asset_slug(symbol)

            # Set default time range if not provided
            if start is None or end is None:
                end = datetime.utcnow()
                start = end - timedelta(days=1)

            url = self._build_api_url(asset_slug, start, end, self.default_limit)
            print("-----------------url")
            print(url)
            log_event(
                stage="ingestion",
                block="adapter",
                level="DEBUG",
                msg="Fetching news data from API",
                extra={
                    "adapter_id": self.adapter_id,
                    "symbol": symbol,
                    "asset_slug": asset_slug,
                    "url": url,
                    "start": start.isoformat(),
                    "end": end.isoformat(),
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
                            extra={
                                "status": response.status,
                                "response": text[:200],
                                "symbol": symbol,
                            },
                        )
                        self.log_error(symbol, error_msg)
                        return {
                            "success": False,
                            "error": error_msg,
                            "vendor": self.vendor,
                            "status_code": response.status,
                        }

                    api_response = await response.json()

            # Check API response success flag
            if not api_response.get("success", False):
                error_msg = "API returned success=false"
                log_event(
                    stage="ingestion",
                    block="adapter",
                    level="ERROR",
                    msg=error_msg,
                    extra={
                        "symbol": symbol,
                        "asset_slug": asset_slug,
                        "api_response": str(api_response)[:200],
                    },
                )
                self.log_error(symbol, error_msg)
                return {
                    "success": False,
                    "error": error_msg,
                    "vendor": self.vendor,
                }

            # Extract data from response
            news_data = api_response.get("data", [])
            pagination = api_response.get("pagination", {})

            if not news_data:
                log_event(
                    stage="ingestion",
                    block="adapter",
                    level="WARNING",
                    msg=f"No news data returned for symbol {symbol}",
                    extra={
                        "adapter_id": self.adapter_id,
                        "symbol": symbol,
                        "asset_slug": asset_slug,
                    },
                )
                # Return empty result but still valid format
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
                    "record_count": 0,
                    "metadata": {
                        "pagination": pagination,
                        "asset_slug": asset_slug,
                    },
                }

            # Transform API response to match schema
            transformed_data = self._transform_api_response(
                news_data, symbol, start, end
            )

            # Validate schema for transformed data
            self.validate_schema(transformed_data)

            record_count = len(news_data)

            log_event(
                stage="ingestion",
                block="adapter",
                level="INFO",
                msg=f"Successfully ingested {record_count} news articles",
                extra={
                    "adapter_id": self.adapter_id,
                    "symbol": symbol,
                    "asset_slug": asset_slug,
                    "record_count": record_count,
                    "mode": "latest" if (start is None or end is None) else "range",
                    "pagination": pagination,
                },
            )

            self.log_success(symbol, record_count=record_count)

            return {
                "success": True,
                "data": transformed_data,
                "vendor": self.vendor,
                "ingested_at": datetime.utcnow().isoformat(),
                "record_count": record_count,
                "metadata": {
                    "pagination": pagination,
                    "asset_slug": asset_slug,
                    "time_range": {
                        "start": start.isoformat(),
                        "end": end.isoformat(),
                    },
                },
            }

        except aiohttp.ClientError as e:
            error_msg = f"Network error: {str(e)}"
            self.log_error(symbol, error_msg)
            return {
                "success": False,
                "error": error_msg,
                "vendor": self.vendor,
            }

        except Exception as e:
            error_msg = f"Unexpected error: {str(e)}"
            self.log_error(symbol, error_msg)
            return {
                "success": False,
                "error": error_msg,
                "vendor": self.vendor,
            }


# Example usage
if __name__ == "__main__":
    import asyncio

    config = {
        "vendor": "internal_news_api",
        "id": "news_internal_001",
        "cadence": "5min",
        "schema_type": "news",
        "limit": 100,
    }

    adapter = ResilientNewsAdapter(config)

    print("\n=== Fetch latest news (last 24 hours) ===")
    latest = asyncio.run(adapter.execute_ingest("bitcoin"))
    print(f"Success: {latest.get('success')}")
    print(f"Records: {latest.get('record_count', 0)}")
    if latest.get("success") and latest.get("data"):
        print(f"Sample article: {latest['data']['data'][0]['title']}")

    print("\n=== Fetch news for specific time range ===")
    end = datetime.utcnow()
    start = end - timedelta(hours=6)
    ranged = asyncio.run(
        adapter.execute_ingest("BINANCE:BTCUSDT.P", start=start, end=end)
    )
    print(f"Success: {ranged.get('success')}")
    print(f"Records: {ranged.get('record_count', 0)}")
