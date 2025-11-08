"""
Unit tests for adapters
Run with: pytest tests/test_adapters.py -v
"""

import pytest
from src.adapters.price_adapter import ResilientPriceAdapter
from src.adapters.news_adapter import ResilientNewsAdapter
from src.adapters.fundamental_adapter import ResilientFundamentalAdapter


@pytest.mark.asyncio
async def test_price_adapter_basic():
    """Test price adapter returns structured data"""
    config = {
        "vendor": "yfinance",
        "id": "test_price_001",
        "cadence": "1min",
        "schema_type": "price",
    }

    adapter = ResilientPriceAdapter(config)
    result = await adapter.execute_ingest("AAPL")

    assert result["success"]
    assert "data" in result
    assert result["data"]["symbol"] == "AAPL"


@pytest.mark.asyncio
async def test_news_adapter_basic():
    """Test news adapter returns structured data"""
    config = {
        "vendor": "alphavantage",
        "id": "test_news_001",
        "cadence": "daily",
        "schema_type": "news",
    }

    adapter = ResilientNewsAdapter(config)
    result = await adapter.execute_ingest("AAPL")

    assert result["success"]
    assert "data" in result
    assert result["data"]["symbol"] == "AAPL"
    assert isinstance(result["data"]["data"], list)


@pytest.mark.asyncio
async def test_fundamental_adapter_basic():
    """Test fundamental adapter returns structured data"""
    config = {
        "vendor": "fmp",
        "id": "test_fundamental_001",
        "cadence": "daily",
        "schema_type": "fundamental",
    }

    adapter = ResilientFundamentalAdapter(config)
    result = await adapter.execute_ingest("AAPL")

    assert result["success"]
    assert "data" in result
    assert result["data"]["symbol"] == "AAPL"
    assert "data" in result["data"]


@pytest.mark.asyncio
async def test_all_adapters_run_independently():
    """Test all three adapters can run independently"""

    configs = [
        {
            "vendor": "yfinance",
            "id": "price_001",
            "cadence": "1min",
            "schema_type": "price",
        },
        {
            "vendor": "alphavantage",
            "id": "news_001",
            "cadence": "daily",
            "schema_type": "news",
        },
        {
            "vendor": "fmp",
            "id": "fundamental_001",
            "cadence": "daily",
            "schema_type": "fundamental",
        },
    ]

    price_adapter = ResilientPriceAdapter(configs[0])
    news_adapter = ResilientNewsAdapter(configs[1])
    fundamental_adapter = ResilientFundamentalAdapter(configs[2])

    price_result = await price_adapter.execute_ingest("TSLA")
    news_result = await news_adapter.execute_ingest("TSLA")
    fundamental_result = await fundamental_adapter.execute_ingest("TSLA")

    assert price_result["success"]
    assert news_result["success"]
    assert fundamental_result["success"]


@pytest.mark.asyncio
async def test_adapter_logs_to_correct_directory():
    """Test that adapters log to /logs/adapters/"""
    from pathlib import Path

    config = {
        "vendor": "yfinance",
        "id": "test_log_001",
        "cadence": "1min",
        "schema_type": "price",
    }
    adapter = ResilientPriceAdapter(config)

    _ = await adapter.execute_ingest("AAPL")

    log_dir = Path("logs/adapters")
    log_files = list(log_dir.glob("*.jsonl"))

    assert len(log_files) > 0, "No adapter log files found"


@pytest.mark.asyncio
async def test_schema_validation_happens():
    """Test that schema validation is performed"""
    from pathlib import Path

    config = {
        "vendor": "yfinance",
        "id": "test_validation_001",
        "cadence": "1min",
        "schema_type": "price",
    }

    adapter = ResilientPriceAdapter(config)
    _ = await adapter.execute_ingest("AAPL")

    log_dir = Path("logs/adapters")
    log_files = list(log_dir.glob("*.jsonl"))

    validation_logged = False
    for log_file in log_files:
        with open(log_file, "r") as f:
            for line in f:
                if "Schema validation passed" in line:
                    validation_logged = True
                    break

    assert validation_logged, "Schema validation was not logged"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
