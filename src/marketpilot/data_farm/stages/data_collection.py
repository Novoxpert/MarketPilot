"""
Data Collection Stage - Process already fetched data
"""

from typing import Dict, Any
from marketpilot.data_farm.stages.base_stage import BaseStage
from marketpilot.utils.logger import log_event


class DataCollectionStage(BaseStage):
    """Process and organize already fetched data"""

    def __init__(self):
        super().__init__("data_collection")

    async def _process(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process fetched data into standardized format

        This stage now works with data already fetched by ResilientDataFarm.fetch_data_for_symbols()
        instead of calling adapters again
        """

        # Get raw_data that was already fetched
        raw_data_by_type = data.get("raw_data", {})

        if not raw_data_by_type:
            log_event(
                stage=self.stage_name,
                block="data_collection",
                level="WARNING",
                msg="No raw_data found - was fetch_data_for_symbols() called?",
            )
            data["raw_data"] = []
            return data

        # Get config to find adapter mappings
        config = data.get("config", {})
        adapters_config = config.get("adapters", [])

        # Build adapter mapping: type -> adapter info
        adapter_mapping = {}
        for adapter_cfg in adapters_config:
            adapter_type = adapter_cfg.get("type")
            if adapter_type:
                adapter_mapping[adapter_type] = {
                    "id": adapter_cfg.get("id", f"{adapter_type}_unknown"),
                    "vendor": adapter_cfg.get("vendor", "unknown"),
                }

        collected_records = []

        # Process price data
        if "price" in raw_data_by_type:
            adapter_info = adapter_mapping.get(
                "price", {"id": "price_unknown", "vendor": "unknown"}
            )

            for symbol, records in raw_data_by_type["price"].items():
                if isinstance(records, list):
                    for record in records:
                        collected_records.append(
                            {
                                "adapter_id": adapter_info["id"],
                                "symbol": symbol,
                                "vendor": adapter_info["vendor"],
                                "schema_type": "price",
                                "data": record,
                                "ingested_at": record.get(
                                    "timestamp", record.get("candle_time")
                                ),
                            }
                        )
                else:
                    # Single record (old adapter format)
                    collected_records.append(
                        {
                            "adapter_id": adapter_info["id"],
                            "symbol": symbol,
                            "vendor": adapter_info["vendor"],
                            "schema_type": "price",
                            "data": records,
                            "ingested_at": records.get(
                                "timestamp", records.get("candle_time")
                            ),
                        }
                    )

        # Process news data - UPDATED for new structure
        if "news" in raw_data_by_type:
            adapter_info = adapter_mapping.get(
                "news", {"id": "news_unknown", "vendor": "unknown"}
            )

            for symbol, news_response in raw_data_by_type["news"].items():
                # news_response is the full response from adapter with structure:
                # {"symbol": "...", "startdate": "...", "enddate": "...", "timestamp": "...", "data": [...]}

                if isinstance(news_response, dict):
                    # Get the array of news articles from 'data' field
                    news_articles = news_response.get("data", [])

                    # If news_articles is a list, process each article
                    if isinstance(news_articles, list):
                        for article in news_articles:
                            collected_records.append(
                                {
                                    "adapter_id": adapter_info["id"],
                                    "symbol": symbol,
                                    "vendor": adapter_info["vendor"],
                                    "schema_type": "news",
                                    "data": article,
                                    "ingested_at": article.get("published_at_utc"),
                                }
                            )
                    else:
                        # Single article (shouldn't happen with new adapter, but handle it)
                        collected_records.append(
                            {
                                "adapter_id": adapter_info["id"],
                                "symbol": symbol,
                                "vendor": adapter_info["vendor"],
                                "schema_type": "news",
                                "data": news_articles,
                                "ingested_at": (
                                    news_articles.get("published_at_utc")
                                    if isinstance(news_articles, dict)
                                    else None
                                ),
                            }
                        )
                elif isinstance(news_response, list):
                    # Fallback: if it's already a list of articles (old format)
                    for article in news_response:
                        collected_records.append(
                            {
                                "adapter_id": adapter_info["id"],
                                "symbol": symbol,
                                "vendor": adapter_info["vendor"],
                                "schema_type": "news",
                                "data": article,
                                "ingested_at": article.get("published_at_utc"),
                            }
                        )

        # Process fundamental data
        if "fundamental" in raw_data_by_type:
            adapter_info = adapter_mapping.get(
                "fundamental", {"id": "fundamental_unknown", "vendor": "unknown"}
            )

            for symbol, records in raw_data_by_type["fundamental"].items():
                if isinstance(records, list):
                    for record in records:
                        collected_records.append(
                            {
                                "adapter_id": adapter_info["id"],
                                "symbol": symbol,
                                "vendor": adapter_info["vendor"],
                                "schema_type": "fundamental",
                                "data": record,
                                "ingested_at": record.get("date_utc"),
                            }
                        )
                else:
                    collected_records.append(
                        {
                            "adapter_id": adapter_info["id"],
                            "symbol": symbol,
                            "vendor": adapter_info["vendor"],
                            "schema_type": "fundamental",
                            "data": records,
                            "ingested_at": records.get("date_utc"),
                        }
                    )

        log_event(
            stage=self.stage_name,
            block="data_collection",
            level="INFO",
            msg=f"Organized {len(collected_records)} records from fetched data",
            extra={
                "total_records": len(collected_records),
                "unique_symbols": len(set(r["symbol"] for r in collected_records)),
                "schema_types": list(
                    set(r.get("schema_type", "unknown") for r in collected_records)
                ),
                "adapter_mapping": adapter_mapping,
            },
        )

        # Replace raw_data with organized records
        data["raw_data"] = collected_records
        return data
