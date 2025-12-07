"""
Simple tests for pipeline stages with Mode Manager integration
"""

import pytest
from marketpilot.data_farm.stages.nan_processing import NaNProcessingStage
from marketpilot.data_farm.stages.deduplication import DeduplicationStage
from marketpilot.data_farm.stages.temporal_alignment import TemporalAlignmentStage
from marketpilot.data_farm.stages.quality_assurance import QualityAssuranceStage
from marketpilot.utils.mode_manager import set_test_mode


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
# NaN Processing Stage Tests
# ========================================

@pytest.mark.unit
@pytest.mark.stage
@pytest.mark.asyncio
async def test_nan_processing_basic():
    """Test basic NaN processing"""
    stage = NaNProcessingStage()
    
    # Test data with NaN values
    test_data = {
        "raw_data": [
            {
                "adapter_id": "test",
                "symbol": "BTCUSDT",
                "vendor": "test",
                "schema_type": "price",
                "data": {
                    "symbol": "BTCUSDT",
                    "open": None,  # NaN value
                    "close": 95000.0,
                    "volume": 0
                }
            }
        ]
    }
    
    result = await stage._process(test_data)
    
    assert "processed_data" in result
    assert "nan_stats" in result
    assert result["nan_stats"]["nan_count"] >= 1
    
    # Verify NaN was handled
    processed_record = result["processed_data"][0]
    assert processed_record["data"]["open"] is not None


@pytest.mark.unit
@pytest.mark.stage
@pytest.mark.asyncio
async def test_nan_processing_empty_data():
    """Test empty data handling"""
    stage = NaNProcessingStage()
    
    test_data = {"raw_data": []}
    result = await stage._process(test_data)
    
    assert result["processed_data"] == []
    assert result["nan_stats"]["nan_count"] == 0


# ========================================
# Temporal Alignment Stage Tests
# ========================================

@pytest.mark.unit
@pytest.mark.stage
@pytest.mark.asyncio
async def test_temporal_alignment_iso_string():
    """Test ISO string to Unix ms conversion"""
    stage = TemporalAlignmentStage()
    
    test_data = {
        "processed_data": [
            {
                "adapter_id": "test",
                "symbol": "BTCUSDT",
                "vendor": "test",
                "schema_type": "price",
                "data": {
                    "symbol": "BTCUSDT",
                    "candle_time": "2025-01-15T10:00:00Z",
                    "close": 95000.0
                }
            }
        ]
    }
    
    result = await stage._process(test_data)
    
    assert "aligned_data" in result
    assert "alignment_stats" in result
    
    # Verify timestamp was added
    aligned_record = result["aligned_data"][0]
    assert "timestamp" in aligned_record["data"]
    assert isinstance(aligned_record["data"]["timestamp"], int)


@pytest.mark.unit
@pytest.mark.stage
@pytest.mark.asyncio
async def test_temporal_alignment_unix_seconds():
    """Test Unix seconds to Unix ms conversion"""
    stage = TemporalAlignmentStage()
    
    test_data = {
        "processed_data": [
            {
                "adapter_id": "test",
                "symbol": "BTCUSDT",
                "vendor": "test",
                "schema_type": "price",
                "data": {
                    "symbol": "BTCUSDT",
                    "timestamp": 1736935200,  # Unix seconds
                    "close": 95000.0
                }
            }
        ]
    }
    
    result = await stage._process(test_data)
    
    aligned_record = result["aligned_data"][0]
    # Should be converted to milliseconds
    assert aligned_record["data"]["timestamp"] > 1000000000000


# ========================================
# Deduplication Stage Tests
# ========================================

@pytest.mark.unit
@pytest.mark.stage
@pytest.mark.asyncio
async def test_deduplication_removes_duplicates():
    """Test duplicate record removal"""
    stage = DeduplicationStage()
    
    # Data with duplicates
    test_data = {
        "aligned_data": [
            {
                "adapter_id": "test",
                "symbol": "BTCUSDT",
                "vendor": "test",
                "schema_type": "price",
                "data": {
                    "symbol": "BTCUSDT",
                    "timestamp": 1736935200000,
                    "close": 95000.0
                }
            },
            {
                "adapter_id": "test",
                "symbol": "BTCUSDT",
                "vendor": "test",
                "schema_type": "price",
                "data": {
                    "symbol": "BTCUSDT",
                    "timestamp": 1736935200000,  # Same timestamp
                    "close": 95100.0
                }
            }
        ]
    }
    
    result = await stage._process(test_data)
    
    assert "unique_data" in result
    assert "dedup_stats" in result
    
    # One should be removed
    assert len(result["unique_data"]) == 1
    assert result["dedup_stats"]["duplicates_removed"] == 1


@pytest.mark.unit
@pytest.mark.stage
@pytest.mark.asyncio
async def test_deduplication_no_duplicates():
    """Test with no duplicates"""
    stage = DeduplicationStage()
    
    test_data = {
        "aligned_data": [
            {
                "adapter_id": "test",
                "symbol": "BTCUSDT",
                "vendor": "test",
                "schema_type": "price",
                "data": {
                    "symbol": "BTCUSDT",
                    "timestamp": 1736935200000,
                    "close": 95000.0
                }
            },
            {
                "adapter_id": "test",
                "symbol": "BTCUSDT",
                "vendor": "test",
                "schema_type": "price",
                "data": {
                    "symbol": "BTCUSDT",
                    "timestamp": 1736935260000,  # Different timestamp
                    "close": 95100.0
                }
            }
        ]
    }
    
    result = await stage._process(test_data)
    
    # Nothing should be removed
    assert len(result["unique_data"]) == 2
    assert result["dedup_stats"]["duplicates_removed"] == 0


# ========================================
# Quality Assurance Stage Tests
# ========================================

@pytest.mark.unit
@pytest.mark.stage
@pytest.mark.asyncio
async def test_qa_pass():
    """Test successful QA validation"""
    stage = QualityAssuranceStage()
    
    test_data = {
        "unique_data": [
            {
                "adapter_id": "test",
                "symbol": "BTCUSDT",
                "vendor": "test",
                "schema_type": "price",
                "data": {
                    "symbol": "BTCUSDT",
                    "timestamp": 1736935200000,
                    "close": 95000.0
                }
            }
        ],
        "config": {
            "quality": {
                "quality_threshold": 0.95
            }
        }
    }
    
    result = await stage._process(test_data)
    
    assert "validated_data" in result
    assert "qa_stats" in result
    assert result["qa_stats"]["qa_passed"] == 1
    assert result["qa_stats"]["qa_failed"] == 0


@pytest.mark.unit
@pytest.mark.stage
@pytest.mark.asyncio
async def test_qa_fail_missing_symbol():
    """Test QA failure with missing symbol"""
    stage = QualityAssuranceStage()
    
    test_data = {
        "unique_data": [
            {
                "adapter_id": "test",
                "symbol": None,  # Missing symbol
                "vendor": "test",
                "schema_type": "price",
                "data": {
                    "timestamp": 1736935200000,
                    "close": 95000.0
                }
            }
        ],
        "config": {
            "quality": {
                "quality_threshold": 0.95
            }
        }
    }
    
    result = await stage._process(test_data)
    
    # Should be rejected
    assert result["qa_stats"]["qa_passed"] == 0
    assert result["qa_stats"]["qa_failed"] == 1


@pytest.mark.unit
@pytest.mark.stage
@pytest.mark.asyncio
async def test_qa_fail_empty_data():
    """Test QA failure with empty data"""
    stage = QualityAssuranceStage()
    
    test_data = {
        "unique_data": [
            {
                "adapter_id": "test",
                "symbol": "BTCUSDT",
                "vendor": "test",
                "schema_type": "price",
                "data": {}  # Empty data
            }
        ],
        "config": {
            "quality": {
                "quality_threshold": 0.95
            }
        }
    }
    
    result = await stage._process(test_data)
    
    # Should be rejected
    assert result["qa_stats"]["qa_passed"] == 0
    assert result["qa_stats"]["qa_failed"] == 1