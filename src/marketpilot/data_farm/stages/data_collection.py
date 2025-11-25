"""
Data Collection Stage - Process already fetched data
Fixed to properly handle news data structure
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
                # Handle list of records (new API format)
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

        # Process news data 
        if "news" in raw_data_by_type:
            adapter_info = adapter_mapping.get(
                "news", {"id": "news_unknown", "vendor": "unknown"}
            )

            for symbol, news_response in raw_data_by_type["news"].items():
                # {"symbol": "...", "startdate": "...", "enddate": "...", "timestamp": "...", "data": [...]}

                log_event(
                    stage=self.stage_name,
                    block="data_collection",
                    level="DEBUG",
                    msg=f"Processing news for {symbol}",
                    extra={
                        "symbol": symbol,
                        "response_type": type(news_response).__name__,
                        "has_data_field": "data" in news_response
                        if isinstance(news_response, dict)
                        else False,
                    },
                )

                if isinstance(news_response, dict) and "data" in news_response:
                    # Get the array of news articles from 'data' field
                    news_articles = news_response.get("data", [])

                    log_event(
                        stage=self.stage_name,
                        block="data_collection",
                        level="DEBUG",
                        msg=f"Found {len(news_articles) if isinstance(news_articles, list) else 0} articles for {symbol}",
                    )

                    # If news_articles is a list, process each article
                    if isinstance(news_articles, list):
                        for article in news_articles:
                            if isinstance(article, dict):
                                collected_records.append(
                                    {
                                        "adapter_id": adapter_info["id"],
                                        "symbol": symbol,
                                        "vendor": adapter_info["vendor"],
                                        "schema_type": "news",
                                        "data": article,
                                        "ingested_at": article.get(
                                            "published_at_utc",
                                            article.get("releasedAt"),
                                        ),
                                    }
                                )
                    else:
                        log_event(
                            stage=self.stage_name,
                            block="data_collection",
                            level="WARNING",
                            msg=f"Unexpected news data format for {symbol} - not a list",
                        )
                        if isinstance(news_articles, dict):
                            collected_records.append(
                                {
                                    "adapter_id": adapter_info["id"],
                                    "symbol": symbol,
                                    "vendor": adapter_info["vendor"],
                                    "schema_type": "news",
                                    "data": news_articles,
                                    "ingested_at": news_articles.get(
                                        "published_at_utc",
                                        news_articles.get("releasedAt"),
                                    ),
                                }
                            )
                elif isinstance(news_response, list):
                    # Fallback: if it's already a list of articles (shouldn't happen)
                    log_event(
                        stage=self.stage_name,
                        block="data_collection",
                        level="WARNING",
                        msg=f"News response is already a list for {symbol} - processing directly",
                    )
                    for article in news_response:
                        if isinstance(article, dict):
                            collected_records.append(
                                {
                                    "adapter_id": adapter_info["id"],
                                    "symbol": symbol,
                                    "vendor": adapter_info["vendor"],
                                    "schema_type": "news",
                                    "data": article,
                                    "ingested_at": article.get(
                                        "published_at_utc", article.get("releasedAt")
                                    ),
                                }
                            )
                else:
                    log_event(
                        stage=self.stage_name,
                        block="data_collection",
                        level="ERROR",
                        msg=f"Unexpected news data structure for {symbol}",
                        extra={
                            "symbol": symbol,
                            "type": type(news_response).__name__,
                        },
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
                "by_type": {
                    "price": len(
                        [
                            r
                            for r in collected_records
                            if r.get("schema_type") == "price"
                        ]
                    ),
                    "news": len(
                        [r for r in collected_records if r.get("schema_type") == "news"]
                    ),
                    "fundamental": len(
                        [
                            r
                            for r in collected_records
                            if r.get("schema_type") == "fundamental"
                        ]
                    ),
                },
                "adapter_mapping": adapter_mapping,
            },
        )

        # Replace raw_data with organized records
        data["raw_data"] = collected_records
        return data
