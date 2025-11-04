"""
Story MP-004
Unit tests for adapters
Run with: pytest tests/test_adapters.py -v
"""

import pytest
from adapters.price_adapter import ResilientPriceAdapter
from adapters.news_adapter import ResilientNewsAdapter
from adapters.fundamental_adapter import ResilientFundamentalAdapter
from data_farm.config.config_loader import validate_data_columns
from pathlib import Path


@pytest.mark.asyncio
async def test_price_adapter_basic():
    """Test price adapter returns structured data."""
    config = {"vendor": "yfinance", "id": "test_price_001", "cadence": "1min"}

    adapter = ResilientPriceAdapter(config)
    result = await adapter.execute_ingest("AAPL")

    # Validate response structure
    assert result["success"]
    assert "data" in result
    assert result["data"]["symbol"] == "AAPL"

    # Validate schema
    assert validate_data_columns(result["data"], "price")


@pytest.mark.asyncio
async def test_news_adapter_basic():
    """Test news adapter returns structured data."""
    config = {"vendor": "alphavantage", "id": "test_news_001", "cadence": "daily"}

    adapter = ResilientNewsAdapter(config)
    result = await adapter.execute_ingest("AAPL")

    # Validate response structure
    assert result["success"]
    assert "data" in result
    assert result["data"]["symbol"] == "AAPL"
    assert isinstance(result["data"]["data"], list)

    # Validate schema
    assert validate_data_columns(result["data"], "news")


@pytest.mark.asyncio
async def test_fundamental_adapter_basic():
    """Test fundamental adapter returns structured data."""
    config = {"vendor": "fmp", "id": "test_fundamental_001", "cadence": "daily"}

    adapter = ResilientFundamentalAdapter(config)
    result = await adapter.execute_ingest("AAPL")

    # Validate response structure
    assert result["success"]
    assert "data" in result
    assert result["data"]["symbol"] == "AAPL"
    assert "data" in result["data"]

    # Validate schema
    assert validate_data_columns(result["data"], "fundamental")


@pytest.mark.asyncio
async def test_all_adapters_run_independently():
    """Ensure all adapters can run independently without conflicts."""
    configs = [
        {"vendor": "yfinance", "id": "price_001", "cadence": "1min"},
        {"vendor": "alphavantage", "id": "news_001", "cadence": "daily"},
        {"vendor": "fmp", "id": "fundamental_001", "cadence": "daily"},
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
    """Verify adapters log output to /logs/adapters/ directory."""
    config = {"vendor": "yfinance", "id": "test_log_001", "cadence": "1min"}
    adapter = ResilientPriceAdapter(config)

    await adapter.execute_ingest("AAPL")

    log_dir = Path("logs/adapters")
    log_files = list(log_dir.glob("*.jsonl"))

    assert log_files, "No adapter log files found."


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
