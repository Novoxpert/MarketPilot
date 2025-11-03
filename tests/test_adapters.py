"""Story MP-004
Unit tests for adapters
Run with: pytest tests/test_adapters.py -v
"""
import pytest
import asyncio
from adapters.price_adapter import ResilientPriceAdapter
from adapters.news_adapter import ResilientNewsAdapter
from adapters.fundamental_adapter import ResilientFundamentalAdapter
from data_farm.config.config_loader import validate_data_columns


@pytest.mark.asyncio
async def test_price_adapter_basic():
    """Test price adapter returns structured data"""
    config = {
        "vendor": "yfinance",
        "id": "test_price_001",
        "cadence": "1min"
    }
    
    adapter = ResilientPriceAdapter(config)
    result = await adapter.execute_ingest("AAPL")
    
    # Check response structure
    assert result["success"] == True
    assert "data" in result
    assert result["data"]["symbol"] == "AAPL"
    
    # Validate against schema
    assert validate_data_columns(result["data"], "price")


@pytest.mark.asyncio
async def test_news_adapter_basic():
    """Test news adapter returns structured data"""
    config = {
        "vendor": "alphavantage",
        "id": "test_news_001",
        "cadence": "daily"
    }
    
    adapter = ResilientNewsAdapter(config)
    result = await adapter.execute_ingest("AAPL")
    
    # Check response structure
    assert result["success"] == True
    assert "data" in result
    assert result["data"]["symbol"] == "AAPL"
    assert isinstance(result["data"]["data"], list)
    
    # Validate against schema
    assert validate_data_columns(result["data"], "news")


@pytest.mark.asyncio
async def test_fundamental_adapter_basic():
    """Test fundamental adapter returns structured data"""
    config = {
        "vendor": "fmp",
        "id": "test_fundamental_001",
        "cadence": "daily"
    }
    
    adapter = ResilientFundamentalAdapter(config)
    result = await adapter.execute_ingest("AAPL")
    
    # Check response structure
    assert result["success"] == True
    assert "data" in result
    assert result["data"]["symbol"] == "AAPL"
    assert "data" in result["data"]
    
    # Validate against schema
    assert validate_data_columns(result["data"], "fundamental")


@pytest.mark.asyncio
async def test_all_adapters_run_independently():
    """Test all three adapters can run independently"""
    
    configs = [
        {"vendor": "yfinance", "id": "price_001", "cadence": "1min"},
        {"vendor": "alphavantage", "id": "news_001", "cadence": "daily"},
        {"vendor": "fmp", "id": "fundamental_001", "cadence": "daily"}
    ]
    
    price_adapter = ResilientPriceAdapter(configs[0])
    news_adapter = ResilientNewsAdapter(configs[1])
    fundamental_adapter = ResilientFundamentalAdapter(configs[2])
    
    # Run all adapters
    price_result = await price_adapter.execute_ingest("TSLA")
    news_result = await news_adapter.execute_ingest("TSLA")
    fundamental_result = await fundamental_adapter.execute_ingest("TSLA")
    
    # All should succeed
    assert price_result["success"] == True
    assert news_result["success"] == True
    assert fundamental_result["success"] == True


@pytest.mark.asyncio
async def test_adapter_logs_to_correct_directory():
    """Test that adapters log to /logs/adapters/"""
    from pathlib import Path
    
    config = {"vendor": "yfinance", "id": "test_log_001", "cadence": "1min"}
    adapter = ResilientPriceAdapter(config)
    
    await adapter.execute_ingest("AAPL")
    
    # Check that adapter logs exist
    log_dir = Path("logs/adapters")
    log_files = list(log_dir.glob("*.jsonl"))
    
    assert len(log_files) > 0, "No adapter log files found"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])