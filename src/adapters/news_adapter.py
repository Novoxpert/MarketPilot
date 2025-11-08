"""
Resilient News Adapter using AlphaVantage
Inherits schema validation from BaseAdapter
"""

from typing import Dict, Any
from datetime import datetime, timedelta
from adapters.base_adapter import BaseAdapter


class ResilientNewsAdapter(BaseAdapter):
    """News data adapter using AlphaVantage"""

    async def execute_ingest(self, symbol: str) -> Dict[str, Any]:
        """
        Ingest news data for a symbol

        Args:
            symbol: Stock symbol (e.g., 'AAPL')

        Returns:
            Dictionary with news data
        """
        try:
            # TODO: Replace with actual AlphaVantage API call
            # For now, return mock data

            end_date = datetime.now()
            start_date = end_date - timedelta(days=1)

            # Mock news data
            mock_news = [
                {
                    "title": f"{symbol} Stock Analysis",
                    "url": "https://example.com/news1",
                    "published_at": datetime.now().isoformat(),
                    "sentiment": "positive",
                },
                {
                    "title": f"{symbol} Quarterly Earnings",
                    "url": "https://example.com/news2",
                    "published_at": (datetime.now() - timedelta(hours=3)).isoformat(),
                    "sentiment": "neutral",
                },
            ]

            result_data = {
                "symbol": symbol,
                "startdate": start_date.isoformat(),
                "enddate": end_date.isoformat(),
                "data": mock_news,
            }

            # ✅ Validate against schema BEFORE returning
            self.validate_schema(result_data)

            self.log_success(symbol, record_count=len(mock_news))

            return {
                "success": True,
                "data": result_data,
                "vendor": self.vendor,
                "ingested_at": datetime.now().isoformat(),
            }

        except Exception as e:
            self.log_error(symbol, str(e))
            return {"success": False, "error": str(e), "vendor": self.vendor}


# Example usage
if __name__ == "__main__":
    import asyncio

    config = {
        "vendor": "alphavantage",
        "id": "news_alphavantage_001",
        "cadence": "daily",
        "schema_type": "news",  # ✅ Added schema type
    }

    adapter = ResilientNewsAdapter(config)
    result = asyncio.run(adapter.execute_ingest("AAPL"))
    print(result)
