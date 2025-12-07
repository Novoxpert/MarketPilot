"""
Simple tests for adapters with Mode Manager integration
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import patch
from marketpilot.data_farm.adapters.price_adapter import ResilientPriceAdapter
from marketpilot.data_farm.adapters.news_adapter import ResilientNewsAdapter
from marketpilot.data_farm.adapters.fundamental_adapter import ResilientFundamentalAdapter
from marketpilot.utils.mode_manager import set_test_mode, get_mode_manager


# ========================================
# Setup/Teardown
# ========================================

@pytest.fixture(scope="session", autouse=True)
def setup_test_mode():
    """Setup test mode for all tests"""
    set_test_mode()
    yield
    # Cleanup after all tests
    # manager = get_mode_manager()
    # try:
    #     manager.cleanup_test_data()
    # except Exception:
    #     pass


# ========================================
# Price Adapter Tests
# ========================================

@pytest.mark.unit
@pytest.mark.adapter
def test_price_adapter_initialization():
    """Test price adapter initialization"""
    config = {
        "id": "test_price",
        "type": "price",
        "vendor": "test_vendor",
        "cadence": "1min",
        "schema_type": "price",
        "limit": 100,
    }
    
    with patch.dict('os.environ', {'PRICE_API_BASE_URL': 'http://test.com'}):
        adapter = ResilientPriceAdapter(config)
        
        assert adapter.adapter_id == "test_price"
        assert adapter.vendor == "test_vendor"
        assert adapter.schema_type == "price"


@pytest.mark.unit
@pytest.mark.adapter
def test_price_adapter_transform_response():
    """Test price data transformation"""
    config = {
        "id": "test_price",
        "type": "price",
        "vendor": "test",
        "schema_type": "price",
    }
    
    with patch.dict('os.environ', {'PRICE_API_BASE_URL': 'http://test.com'}):
        adapter = ResilientPriceAdapter(config)
        
        # Test data
        api_data = [
            {
                "symbol": "BTCUSDT",
                "candle_time": "2025-01-15T10:00:00Z",
                "open": 95000.0,
                "high": 95500.0,
                "low": 94800.0,
                "close": 95200.0,
                "volume": 1234.56
            }
        ]
        
        result = adapter._transform_response(api_data, "BTCUSDT")
        
        assert len(result) == 1
        assert result[0]["symbol"] == "BTCUSDT"
        assert result[0]["open"] == 95000.0
        assert result[0]["close"] == 95200.0


@pytest.mark.unit
@pytest.mark.adapter
def test_price_adapter_empty_response():
    """Test empty response handling"""
    config = {
        "id": "test_price",
        "type": "price",
        "vendor": "test",
        "schema_type": "price",
    }
    
    with patch.dict('os.environ', {'PRICE_API_BASE_URL': 'http://test.com'}):
        adapter = ResilientPriceAdapter(config)
        result = adapter._transform_response([], "BTCUSDT")
        
        assert result == []


# ========================================
# News Adapter Tests
# ========================================

@pytest.mark.unit
@pytest.mark.adapter
def test_news_adapter_initialization():
    """Test news adapter initialization"""
    with patch.dict('os.environ', {'NEWS_API_BASE_URL': 'http://test.com'}):
        config = {
            "id": "test_news",
            "type": "news",
            "vendor": "test_vendor",
            "cadence": "5min",
            "schema_type": "news",
        }
        
        adapter = ResilientNewsAdapter(config)
        
        assert adapter.adapter_id == "test_news"
        assert adapter.vendor == "test_vendor"
        assert adapter.schema_type == "news"


@pytest.mark.unit
@pytest.mark.adapter
def test_news_adapter_transform_response():
    """Test news data transformation"""
    with patch.dict('os.environ', {'NEWS_API_BASE_URL': 'http://test.com'}):
        config = {
            "id": "test_news",
            "type": "news",
            "vendor": "test",
            "schema_type": "news",
        }
        
        adapter = ResilientNewsAdapter(config)
        
        # Test data
        articles = [
            {
                "slug": "article-123",
                "title": "Test News",
                "subtitle": "Test Subtitle",
                "releasedAt": "2025-01-15T10:00:00Z",
                "source": "Reuters",
                "sourceName": "Reuters",
                "sourceUrl": "https://example.com",
                "assets": [{"symbol": "BTCUSDT", "name": "Bitcoin"}]
            }
        ]
        
        start = datetime.utcnow() - timedelta(days=1)
        end = datetime.utcnow()
        
        result = adapter._transform_response(articles, "BTCUSDT", start, end)
        
        assert result["symbol"] == "BTCUSDT"
        assert len(result["data"]) == 1
        assert result["data"][0]["news_id"] == "article-123"
        assert result["data"][0]["title"] == "Test News"


# ========================================
# Fundamental Adapter Tests
# ========================================

@pytest.mark.unit
@pytest.mark.adapter
def test_fundamental_adapter_initialization():
    """Test fundamental adapter initialization"""
    config = {
        "id": "test_fundamental",
        "type": "fundamental",
        "vendor": "test_vendor",
        "cadence": "daily",
        "schema_type": "fundamental",
    }
    
    adapter = ResilientFundamentalAdapter(config)
    
    assert adapter.adapter_id == "test_fundamental"
    assert adapter.vendor == "test_vendor"
    assert adapter.schema_type == "fundamental"


@pytest.mark.unit
@pytest.mark.adapter
def test_fundamental_adapter_generate_mock_stock():
    """Test mock fundamental data generation for stocks"""
    config = {
        "id": "test_fundamental",
        "type": "fundamental",
        "vendor": "test",
        "schema_type": "fundamental",
    }
    
    adapter = ResilientFundamentalAdapter(config)
    
    start = datetime.utcnow() - timedelta(days=365)
    end = datetime.utcnow()
    
    result = adapter._generate_mock_fundamentals("AAPL", start, end)
    
    # Verify structure
    assert "income_statement" in result
    assert "balance_sheet" in result
    assert "cash_flow" in result
    assert "ratios" in result
    
    # Verify key fields
    assert "revenue" in result["income_statement"]
    assert "total_assets" in result["balance_sheet"]


@pytest.mark.unit
@pytest.mark.adapter
def test_fundamental_adapter_generate_mock_crypto():
    """Test mock fundamental data generation for crypto"""
    config = {
        "id": "test_fundamental",
        "type": "fundamental",
        "vendor": "test",
        "schema_type": "fundamental",
    }
    
    adapter = ResilientFundamentalAdapter(config)
    
    start = datetime.utcnow() - timedelta(days=365)
    end = datetime.utcnow()
    
    result = adapter._generate_mock_fundamentals("BINANCE:BTCUSDT.P", start, end)
    
    # Verify crypto structure
    assert "market_data" in result
    assert "metrics" in result
    assert "on_chain" in result
    
    # Verify key fields
    assert "market_cap" in result["market_data"]
    assert "volatility_30d" in result["metrics"]