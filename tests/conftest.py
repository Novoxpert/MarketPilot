"""
Pytest Configuration and Shared Fixtures with Mock Data
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, patch
from marketpilot.utils.mode_manager import set_test_mode, get_mode_manager


# ========================================
# Session-level Setup
# ========================================

def pytest_configure(config):
    """
    Runs before all tests start
    """
    # Activate test mode
    set_test_mode()
    
    # Verify test environment
    manager = get_mode_manager()
    assert manager.is_test_mode, "Test mode not activated!"
    
    print("\n" + "="*60)
    print(" Test Mode Activated")
    print("="*60)
    print(f"Log Directory: {manager.get_log_dir()}")
    print(f"Data Directory: {manager.get_data_dir()}")
    print("="*60 + "\n")


# def pytest_unconfigure(config):
#     """
#     Runs after all tests complete
#     """
#     manager = get_mode_manager()
    
#     print("\n" + "="*60)
#     print(" Cleaning up test data...")
#     print("="*60)
    
#     try:
#         # Cleanup test data
#         manager.cleanup_test_data()
#         print(" Test data cleaned successfully")
#     except Exception as e:
#         print(f"  Cleanup warning: {e}")
    
#     print("="*60 + "\n")


# ========================================
# Session-level Fixtures
# ========================================

@pytest.fixture(scope="session")
def test_mode():
    """
    Fixture to ensure test mode
    """
    manager = get_mode_manager()
    assert manager.is_test_mode
    return manager


@pytest.fixture(scope="session")
def test_log_dir(test_mode):
    """
    Test log directory path
    """
    return test_mode.get_log_dir()


@pytest.fixture(scope="session")
def test_data_dir(test_mode):
    """
    Test data directory path
    """
    return test_mode.get_data_dir()


# ========================================
# Mock Environment Variables
# ========================================

@pytest.fixture(scope="session")
def mock_env_vars():
    """
    Mock environment variables for testing
    """
    return {
        'PRICE_API_BASE_URL': 'http://mock.test.com/api/price',
        'NEWS_API_BASE_URL': 'http://mock.test.com/api/news',
        'FUNDAMENTAL_API_BASE_URL': 'http://mock.test.com/api/fundamental',
        'PRICE_API_HEALTH_URL': 'http://mock.test.com/health/price',
        'NEWS_API_HEALTH_URL': 'http://mock.test.com/health/news',
        'FUNDAMENTAL_API_HEALTH_URL': 'http://mock.test.com/health/fundamental',
    }


@pytest.fixture(scope="session", autouse=True)
def setup_mock_env(mock_env_vars):
    """
    Setup mock environment variables for all tests
    """
    with patch.dict('os.environ', mock_env_vars):
        yield


# ========================================
# Mock Data Fixtures
# ========================================

@pytest.fixture
def mock_price_data():
    """
    Mock price data for testing
    """
    return [
        {
            "symbol": "BINANCE:BTCUSDT.P",
            "candle_time": "2025-12-07T10:00:00Z",
            "open": 95000.0,
            "high": 95500.0,
            "low": 94800.0,
            "close": 95200.0,
            "volume": 1234.56
        },
        {
            "symbol": "BINANCE:BTCUSDT.P",
            "candle_time": "2025-12-07T10:01:00Z",
            "open": 95200.0,
            "high": 95600.0,
            "low": 95000.0,
            "close": 95400.0,
            "volume": 2345.67
        }
    ]


@pytest.fixture
def mock_news_data():
    """
    Mock news data for testing
    """
    return [
        {
            "slug": "bitcoin-reaches-95k",
            "title": "Bitcoin Reaches $95,000 Milestone",
            "subtitle": "Cryptocurrency market shows strong momentum",
            "releasedAt": "2025-12-07T10:00:00Z",
            "source": "crypto_news",
            "sourceName": "Crypto News",
            "sourceUrl": "https://example.com/news/btc-95k",
            "assets": [
                {"symbol": "BINANCE:BTCUSDT.P", "name": "Bitcoin"}
            ]
        },
        {
            "slug": "ethereum-update",
            "title": "Ethereum Network Upgrade Successful",
            "subtitle": "Latest upgrade improves transaction speed",
            "releasedAt": "2025-12-07T09:30:00Z",
            "source": "crypto_news",
            "sourceName": "Crypto News",
            "sourceUrl": "https://example.com/news/eth-upgrade",
            "assets": [
                {"symbol": "BINANCE:ETHUSDT.P", "name": "Ethereum"}
            ]
        }
    ]


@pytest.fixture
def mock_fundamental_data():
    """
    Mock fundamental data for testing (crypto format)
    """
    return {
        "market_data": {
            "market_cap": 1800000000000,
            "volume_24h": 35000000000,
            "circulating_supply": 19600000,
            "total_supply": 21000000,
            "max_supply": 21000000
        },
        "metrics": {
            "volatility_30d": 0.45,
            "sharpe_ratio": 1.2,
            "max_drawdown": -0.45,
            "correlation_btc": 1.0
        },
        "on_chain": {
            "active_addresses_24h": 850000,
            "transaction_count_24h": 350000,
            "avg_transaction_value": 12500,
            "hash_rate": 450000000
        }
    }


# ========================================
# Mock API Response Fixtures
# ========================================

@pytest.fixture
def mock_price_api_response(mock_price_data):
    """
    Mock complete price API response
    """
    return {
        "success": True,
        "data": mock_price_data,
        "pagination": {
            "total": len(mock_price_data),
            "limit": 1000,
            "offset": 0,
            "has_more": False
        }
    }


@pytest.fixture
def mock_news_api_response(mock_news_data):
    """
    Mock complete news API response
    """
    return {
        "success": True,
        "data": mock_news_data,
        "pagination": {
            "total": len(mock_news_data),
            "limit": 100,
            "returned": len(mock_news_data),
            "has_next": False,
            "next_cursor": None
        }
    }


@pytest.fixture
def mock_health_response():
    """
    Mock health check API response
    """
    return {
        "success": True,
        "version": "1.0.0",
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat()
    }


# ========================================
# Mock Adapter Fixtures
# ========================================

@pytest.fixture
def mock_adapter_success(mock_price_data):
    """
    Mock successful adapter response
    """
    return {
        "success": True,
        "data": mock_price_data,
        "record_count": len(mock_price_data),
        "vendor": "mock_vendor",
        "adapter_id": "mock_adapter",
        "ingested_at": datetime.utcnow().isoformat(),
    }


@pytest.fixture
def mock_adapter_failure():
    """
    Mock failed adapter response
    """
    return {
        "success": False,
        "error": "Mock API Error",
        "vendor": "mock_vendor",
        "adapter_id": "mock_adapter",
    }


# ========================================
# Sample Test Data
# ========================================

@pytest.fixture
def sample_symbols():
    """
    Sample symbols for testing
    """
    return [
        "BINANCE:BTCUSDT.P",
        "BINANCE:ETHUSDT.P",
    ]


@pytest.fixture
def sample_config():
    """
    Sample configuration for testing
    """
    return {
        "logging": {"level": "INFO"},
        "output": {
            "base_dir": "data_test",
            "formats": ["parquet"],
            "compression": "snappy"
        },
        "adapters": [
            {
                "id": "test_price",
                "type": "price",
                "vendor": "test",
                "schema_type": "price",
                "limit": 100,
            }
        ],
        "quality": {
            "quality_threshold": 0.80
        }
    }


@pytest.fixture
def sample_date_range():
    """
    Sample date range for testing
    """
    end = datetime.utcnow()
    start = end - timedelta(hours=24)
    return {"start": start, "end": end}


# ========================================
# Markers Configuration
# ========================================

def pytest_collection_modifyitems(config, items):
    """
    Add markers to tests based on file names
    """
    for item in items:
        # Add marker based on file name
        if "test_adapters" in str(item.fspath):
            item.add_marker(pytest.mark.adapter)
        elif "test_stages" in str(item.fspath):
            item.add_marker(pytest.mark.stage)
        elif "test_integration" in str(item.fspath):
            item.add_marker(pytest.mark.integration)


# ========================================
# Test Report Customization
# ========================================

def pytest_report_header(config):
    """
    Add information to report header
    """
    manager = get_mode_manager()
    return [
        f"Test Mode: {manager.mode.value}",
        f"Log Directory: {manager.get_log_dir()}",
        f"Data Directory: {manager.get_data_dir()}",
        "Mock Data: Enabled (No real API calls)",
    ]


# ========================================
# Async Test Support
# ========================================

@pytest.fixture
def event_loop():
    """
    Event loop for async tests
    """
    import asyncio
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()