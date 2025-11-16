"""
Extended unit tests for adapters (MP-010)
Add these tests to your existing test_adapters.py or use as separate file
Run with: pytest tests/test_adapters_extended.py -v
"""

import pytest
from unittest.mock import patch
from marketpilot.adapters.price_adapter import ResilientPriceAdapter
from marketpilot.adapters.news_adapter import ResilientNewsAdapter
from marketpilot.adapters.fundamental_adapter import ResilientFundamentalAdapter


# ═══════════════════════════════════════════════════════════════
# Additional Price Adapter Tests
# ═══════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_price_adapter_numeric_fields():
    """Test that price fields are numeric"""
    config = {
        "vendor": "yfinance",
        "id": "test_numeric_001",
        "cadence": "1min",
        "schema_type": "price",
    }

    adapter = ResilientPriceAdapter(config)
    result = await adapter.execute_ingest("AAPL")

    data = result["data"]
    assert isinstance(data["open"], (int, float))
    assert isinstance(data["high"], (int, float))
    assert isinstance(data["low"], (int, float))
    assert isinstance(data["close"], (int, float))
    assert isinstance(data["volume"], (int, float))


@pytest.mark.asyncio
async def test_price_adapter_timestamp_exists():
    """Test that timestamp field exists"""
    config = {
        "vendor": "yfinance",
        "id": "test_timestamp_001",
        "cadence": "1min",
        "schema_type": "price",
    }

    adapter = ResilientPriceAdapter(config)
    result = await adapter.execute_ingest("GOOGL")

    assert "timestamp" in result["data"]
    assert result["data"]["timestamp"] is not None


@pytest.mark.asyncio
async def test_price_adapter_error_handling():
    """Test adapter handles errors gracefully"""
    config = {
        "vendor": "yfinance",
        "id": "test_error_001",
        "cadence": "1min",
        "schema_type": "price",
    }

    adapter = ResilientPriceAdapter(config)

    # Mock the internal method to raise error
    with patch.object(
        adapter, "_execute_ingest_internal", side_effect=Exception("API Error")
    ):
        result = await adapter.execute_ingest("AAPL")

        assert result["success"] is False
        assert "error" in result
        assert "API Error" in result["error"]


@pytest.mark.asyncio
async def test_price_adapter_multiple_symbols():
    """Test adapter works for multiple symbols"""
    config = {
        "vendor": "yfinance",
        "id": "test_multi_001",
        "cadence": "1min",
        "schema_type": "price",
    }

    adapter = ResilientPriceAdapter(config)
    symbols = ["AAPL", "GOOGL", "MSFT", "TSLA"]

    for symbol in symbols:
        result = await adapter.execute_ingest(symbol)
        assert result["success"]
        assert result["data"]["symbol"] == symbol


# ═══════════════════════════════════════════════════════════════
# Additional News Adapter Tests
# ═══════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_news_adapter_has_timestamp():
    """Test news data has timestamp field"""
    config = {
        "vendor": "alphavantage",
        "id": "test_news_timestamp_001",
        "cadence": "daily",
        "schema_type": "news",
    }

    adapter = ResilientNewsAdapter(config)
    result = await adapter.execute_ingest("AAPL")

    assert "timestamp" in result["data"]


@pytest.mark.asyncio
async def test_news_adapter_data_list_not_empty():
    """Test news data list contains items"""
    config = {
        "vendor": "alphavantage",
        "id": "test_news_list_001",
        "cadence": "daily",
        "schema_type": "news",
    }

    adapter = ResilientNewsAdapter(config)
    result = await adapter.execute_ingest("TSLA")

    news_items = result["data"]["data"]
    assert len(news_items) > 0


@pytest.mark.asyncio
async def test_news_adapter_item_structure():
    """Test individual news items have correct structure"""
    config = {
        "vendor": "alphavantage",
        "id": "test_news_structure_001",
        "cadence": "daily",
        "schema_type": "news",
    }

    adapter = ResilientNewsAdapter(config)
    result = await adapter.execute_ingest("AAPL")

    news_items = result["data"]["data"]
    first_item = news_items[0]

    assert "title" in first_item
    assert "url" in first_item
    assert "published_at" in first_item


# ═══════════════════════════════════════════════════════════════
# Additional Fundamental Adapter Tests
# ═══════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_fundamental_adapter_has_timestamp():
    """Test fundamental data has timestamp field"""
    config = {
        "vendor": "fmp",
        "id": "test_fund_timestamp_001",
        "cadence": "daily",
        "schema_type": "fundamental",
    }

    adapter = ResilientFundamentalAdapter(config)
    result = await adapter.execute_ingest("AAPL")

    assert "timestamp" in result["data"]


@pytest.mark.asyncio
async def test_fundamental_adapter_required_sections():
    """Test fundamental data has all required sections"""
    config = {
        "vendor": "fmp",
        "id": "test_fund_sections_001",
        "cadence": "daily",
        "schema_type": "fundamental",
    }

    adapter = ResilientFundamentalAdapter(config)
    result = await adapter.execute_ingest("AAPL")

    data = result["data"]["data"]
    required = ["income_statement", "balance_sheet", "cash_flow", "ratios"]

    for section in required:
        assert section in data, f"Missing section: {section}"


@pytest.mark.asyncio
async def test_fundamental_adapter_numeric_values():
    """Test fundamental data contains numeric values"""
    config = {
        "vendor": "fmp",
        "id": "test_fund_numeric_001",
        "cadence": "daily",
        "schema_type": "fundamental",
    }

    adapter = ResilientFundamentalAdapter(config)
    result = await adapter.execute_ingest("AAPL")

    income = result["data"]["data"]["income_statement"]
    assert isinstance(income["revenue"], (int, float))
    assert isinstance(income["net_income"], (int, float))


# ═══════════════════════════════════════════════════════════════
# Cross-Adapter Tests
# ═══════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_all_adapters_vendor_field():
    """Test all adapters return correct vendor field"""
    configs = [
        {
            "vendor": "yfinance",
            "id": "test_vendor_price",
            "cadence": "1min",
            "schema_type": "price",
        },
        {
            "vendor": "alphavantage",
            "id": "test_vendor_news",
            "cadence": "daily",
            "schema_type": "news",
        },
        {
            "vendor": "fmp",
            "id": "test_vendor_fund",
            "cadence": "daily",
            "schema_type": "fundamental",
        },
    ]

    price_adapter = ResilientPriceAdapter(configs[0])
    news_adapter = ResilientNewsAdapter(configs[1])
    fund_adapter = ResilientFundamentalAdapter(configs[2])

    price_result = await price_adapter.execute_ingest("AAPL")
    news_result = await news_adapter.execute_ingest("AAPL")
    fund_result = await fund_adapter.execute_ingest("AAPL")

    assert price_result["vendor"] == "yfinance"
    assert news_result["vendor"] == "alphavantage"
    assert fund_result["vendor"] == "fmp"


@pytest.mark.asyncio
async def test_all_adapters_ingested_at_field():
    """Test all adapters include ingested_at timestamp"""
    configs = [
        {
            "vendor": "yfinance",
            "id": "test_ingest_price",
            "cadence": "1min",
            "schema_type": "price",
        },
        {
            "vendor": "alphavantage",
            "id": "test_ingest_news",
            "cadence": "daily",
            "schema_type": "news",
        },
        {
            "vendor": "fmp",
            "id": "test_ingest_fund",
            "cadence": "daily",
            "schema_type": "fundamental",
        },
    ]

    price_adapter = ResilientPriceAdapter(configs[0])
    news_adapter = ResilientNewsAdapter(configs[1])
    fund_adapter = ResilientFundamentalAdapter(configs[2])

    price_result = await price_adapter.execute_ingest("AAPL")
    news_result = await news_adapter.execute_ingest("AAPL")
    fund_result = await fund_adapter.execute_ingest("AAPL")

    assert "ingested_at" in price_result
    assert "ingested_at" in news_result
    assert "ingested_at" in fund_result


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
