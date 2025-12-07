"""
Integration Tests with Mode Manager
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import patch, AsyncMock
from pathlib import Path
from marketpilot.data_farm.resilient_data_farm import ResilientDataFarm
from marketpilot.utils.mode_manager import set_test_mode, get_mode_manager


# ========================================
# Setup/Teardown
# ========================================

@pytest.fixture(scope="session", autouse=True)
def setup_test_mode():
    """Setup test mode for all tests"""
    set_test_mode()
    manager = get_mode_manager()
    
    # Verify paths
    assert manager.is_test_mode
    assert manager.get_log_dir() == Path("logs_test")
    assert manager.get_data_dir() == Path("data_test")
    
    yield
    
    # Cleanup after all tests
    try:
        manager.cleanup_test_data()
        print("\n Test data cleaned up successfully")
    except Exception as e:
        print(f"\n Cleanup warning: {e}")


# ========================================
# ResilientDataFarm Tests
# ========================================

@pytest.mark.integration
def test_data_farm_initialization():
    """Test Data Farm initialization"""
    farm = ResilientDataFarm(
        config_path="src/marketpilot/configs/data/data_farm_config.yml"
    )
    
    assert farm is not None
    assert hasattr(farm, 'adapters')
    assert hasattr(farm, 'stages')
    assert len(farm.stages) == 7  # 7 pipeline stages
    
    # Verify test mode
    manager = get_mode_manager()
    assert manager.is_test_mode


@pytest.mark.integration
def test_data_farm_get_adapters():
    """Test adapter retrieval"""
    farm = ResilientDataFarm(
        config_path="src/marketpilot/configs/data/data_farm_config.yml"
    )
    
    adapters = farm.get_adapters()
    
    assert isinstance(adapters, list)
    assert len(adapters) > 0


@pytest.mark.integration
def test_data_farm_get_config():
    """Test configuration retrieval"""
    farm = ResilientDataFarm(
        config_path="src/marketpilot/configs/data/data_farm_config.yml"
    )
    
    config = farm.get_config()
    
    assert isinstance(config, dict)
    assert "adapters" in config
    assert "output" in config


# ========================================
# Smoke Test
# ========================================

@pytest.mark.integration
@pytest.mark.smoke
@pytest.mark.asyncio
async def test_smoke_test_basic(mock_adapter_success):
    """Test basic smoke test"""
    farm = ResilientDataFarm(
        config_path="src/marketpilot/configs/data/data_farm_config.yml"
    )
    
    # Mock execute_ingest
    for adapter in farm.adapters:
        adapter.execute_ingest = AsyncMock(return_value=mock_adapter_success)
    
    # Run smoke test
    result = await farm.run_smoke_test(["BTCUSDT"])
    
    assert result is not None
    assert "success" in result
    assert "total_tests" in result
    assert "passed" in result
    
    # Verify logs in logs_test/
    manager = get_mode_manager()
    log_dir = manager.get_log_dir()
    assert log_dir.exists()


# ========================================
# Complete Pipeline Test (with Mock)
# ========================================

@pytest.mark.integration
@pytest.mark.pipeline
@pytest.mark.asyncio
async def test_complete_pipeline_with_mock(mock_adapter_success):
    """Test complete pipeline with mock data"""
    farm = ResilientDataFarm(
        config_path="src/marketpilot/configs/data/data_farm_config.yml"
    )
    
    # Mock health check
    with patch('aiohttp.ClientSession') as mock_session:
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value={
            "success": True,
            "version": "1.0.0"
        })
        
        mock_session.return_value.__aenter__.return_value.get.return_value.__aenter__.return_value = mock_response
        
        # Mock adapters to return price data
        for adapter in farm.adapters:
            adapter.execute_ingest = AsyncMock(return_value={
                "success": True,
                "data": [{
                    "symbol": "BTCUSDT",
                    "candle_time": "2025-01-15T10:00:00Z",
                    "open": 95000.0,
                    "high": 95500.0,
                    "low": 94800.0,
                    "close": 95200.0,
                    "volume": 1234.56
                }],
                "record_count": 1,
                "vendor": adapter.vendor,
                "adapter_id": adapter.adapter_id,
                "ingested_at": datetime.utcnow().isoformat(),
            })
        
        # Run pipeline
        result = await farm.run_complete_pipeline(
            symbols=["BTCUSDT"],
            start_date=datetime.utcnow() - timedelta(hours=1),
            end_date=datetime.utcnow()
        )
        
        assert result is not None
        assert "pipeline_success" in result
        
        # Verify test mode and log directory
        manager = get_mode_manager()
        assert manager.is_test_mode
        assert manager.get_log_dir().exists()
        
        # Note: data_test directory may or may not exist depending on
        # whether data was actually exported during the test
        # Only check if pipeline was successful
        if result.get("pipeline_success"):
            # If successful, data directory should exist
            assert manager.get_data_dir().exists()


# ========================================
# Error Handling Tests
# ========================================

@pytest.mark.integration
@pytest.mark.asyncio
async def test_pipeline_handles_adapter_failure(mock_adapter_failure):
    """Test adapter failure handling"""
    farm = ResilientDataFarm(
        config_path="src/marketpilot/configs/data/data_farm_config.yml"
    )
    
    # Mock successful health check
    with patch('aiohttp.ClientSession') as mock_session:
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value={
            "success": True,
            "version": "1.0.0"
        })
        
        mock_session.return_value.__aenter__.return_value.get.return_value.__aenter__.return_value = mock_response
        
        # Mock adapter with error
        for adapter in farm.adapters:
            adapter.execute_ingest = AsyncMock(return_value=mock_adapter_failure)
        
        # Run pipeline
        result = await farm.run_complete_pipeline(
            symbols=["BTCUSDT"],
            start_date=datetime.utcnow() - timedelta(hours=1),
            end_date=datetime.utcnow()
        )
        
        # Pipeline should fail
        assert result["pipeline_success"] == False


# ========================================
# Test Mode Path Tests
# ========================================

@pytest.mark.unit
def test_mode_manager_paths():
    """Test test mode paths"""
    manager = get_mode_manager()
    
    assert manager.is_test_mode
    assert manager.get_log_dir() == Path("logs_test")
    assert manager.get_data_dir() == Path("data_test")


@pytest.mark.integration
@pytest.mark.asyncio
async def test_logs_created_in_test_directory():
    """Test log creation in logs_test/"""
    from marketpilot.utils.logger import log_event, get_log_files
    
    # Create test log
    log_event(
        stage="test_stage",
        block="test_block",
        level="INFO",
        msg="Test log message"
    )
    
    # Check log files
    log_files = get_log_files()
    
    # At least one category should have files
    total_files = sum(len(files) for files in log_files.values())
    assert total_files > 0
    
    # Verify log path
    manager = get_mode_manager()
    log_dir = manager.get_log_dir()
    assert log_dir.exists()
    assert str(log_dir) == "logs_test"


# ========================================
# Shared Fixtures
# ========================================

@pytest.fixture
def sample_price_data():
    """Sample price data"""
    return [
        {
            "symbol": "BTCUSDT",
            "candle_time": "2025-01-15T10:00:00Z",
            "open": 95000.0,
            "high": 95500.0,
            "low": 94800.0,
            "close": 95200.0,
            "volume": 1234.56
        },
        {
            "symbol": "BTCUSDT",
            "candle_time": "2025-01-15T10:01:00Z",
            "open": 95200.0,
            "high": 95600.0,
            "low": 95000.0,
            "close": 95400.0,
            "volume": 2345.67
        }
    ]