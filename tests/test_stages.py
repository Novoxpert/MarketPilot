"""
Unit Tests for Pipeline Stages (MP-010)
Tests for all data processing stages
"""

import pytest
from datetime import datetime
from marketpilot.data_farm.stages.health_check import HealthCheckStage
from marketpilot.data_farm.stages.data_collection import DataCollectionStage
from marketpilot.data_farm.stages.nan_processing import NaNProcessingStage
from marketpilot.data_farm.stages.temporal_alignment import TemporalAlignmentStage
from marketpilot.data_farm.stages.deduplication import DeduplicationStage
from marketpilot.data_farm.stages.quality_assurance import QualityAssuranceStage
from marketpilot.data_farm.stages.data_export import DataExportStage


class TestHealthCheckStage:
    """Test Health Check Stage"""

    @pytest.fixture
    def health_check_stage(self):
        return HealthCheckStage()

    @pytest.fixture
    def sample_data(self):
        return {
            "adapters": [
                {"adapter_id": "adapter_001"},
                {"adapter_id": "adapter_002"},
            ]
        }

    @pytest.mark.asyncio
    async def test_health_check_execution(self, health_check_stage, sample_data):
        """Test health check runs successfully"""
        result = await health_check_stage.execute(sample_data)

        assert "health_check" in result
        assert result["health_check"]["total_adapters"] == 2
        assert result["health_check"]["healthy"] == 2

    @pytest.mark.asyncio
    async def test_health_check_empty_adapters(self, health_check_stage):
        """Test health check with no adapters"""
        data = {"adapters": []}
        result = await health_check_stage.execute(data)

        assert result["health_check"]["total_adapters"] == 0


class TestDataCollectionStage:
    """Test Data Collection Stage"""

    @pytest.fixture
    def collection_stage(self):
        return DataCollectionStage()

    @pytest.fixture
    async def mock_adapter(self):
        """Create a mock adapter for testing"""
        from marketpilot.adapters.price_adapter import ResilientPriceAdapter

        config = {
            "vendor": "yfinance",
            "id": "test_collection_001",
            "cadence": "1min",
            "schema_type": "price",
        }
        return ResilientPriceAdapter(config)

    @pytest.mark.asyncio
    async def test_data_collection_basic(self, collection_stage, mock_adapter):
        """Test basic data collection"""
        data = {
            "adapters": [mock_adapter],
            "symbols": ["AAPL", "GOOGL"],
        }

        result = await collection_stage.execute(data)

        assert "raw_data" in result
        assert len(result["raw_data"]) == 2
        assert all(
            record["symbol"] in ["AAPL", "GOOGL"] for record in result["raw_data"]
        )

    @pytest.mark.asyncio
    async def test_data_collection_multiple_adapters(self, collection_stage):
        """Test collection with multiple adapters"""
        from marketpilot.adapters.price_adapter import ResilientPriceAdapter
        from marketpilot.adapters.news_adapter import ResilientNewsAdapter

        price_adapter = ResilientPriceAdapter(
            {
                "vendor": "yfinance",
                "id": "price_001",
                "cadence": "1min",
                "schema_type": "price",
            }
        )

        news_adapter = ResilientNewsAdapter(
            {
                "vendor": "alphavantage",
                "id": "news_001",
                "cadence": "daily",
                "schema_type": "news",
            }
        )

        data = {
            "adapters": [price_adapter, news_adapter],
            "symbols": ["AAPL"],
        }

        result = await collection_stage.execute(data)

        assert "raw_data" in result
        assert len(result["raw_data"]) == 2  # 2 adapters × 1 symbol

    @pytest.mark.asyncio
    async def test_data_collection_empty_symbols(self, collection_stage, mock_adapter):
        """Test collection with empty symbol list"""
        data = {
            "adapters": [mock_adapter],
            "symbols": [],
        }

        result = await collection_stage.execute(data)

        assert "raw_data" in result
        assert len(result["raw_data"]) == 0

    @pytest.mark.asyncio
    async def test_data_collection_adapter_error_handling(self, collection_stage):
        """Test that collection continues when one adapter fails"""
        from unittest.mock import AsyncMock, MagicMock

        # Create a mock adapter that fails
        failing_adapter = MagicMock()
        failing_adapter.adapter_id = "failing_adapter"
        failing_adapter.execute_ingest = AsyncMock(side_effect=Exception("API Error"))

        # Create a working adapter
        from marketpilot.adapters.price_adapter import ResilientPriceAdapter

        working_adapter = ResilientPriceAdapter(
            {
                "vendor": "yfinance",
                "id": "working_001",
                "cadence": "1min",
                "schema_type": "price",
            }
        )

        data = {
            "adapters": [failing_adapter, working_adapter],
            "symbols": ["AAPL"],
        }

        result = await collection_stage.execute(data)

        # Should have collected data from working adapter despite failure
        assert "raw_data" in result
        assert len(result["raw_data"]) == 1  # Only working adapter succeeded

    @pytest.mark.asyncio
    async def test_data_collection_record_structure(
        self, collection_stage, mock_adapter
    ):
        """Test that collected records have correct structure"""
        data = {
            "adapters": [mock_adapter],
            "symbols": ["AAPL"],
        }

        result = await collection_stage.execute(data)

        record = result["raw_data"][0]
        required_fields = ["adapter_id", "symbol", "vendor", "data", "ingested_at"]

        for field in required_fields:
            assert field in record, f"Missing field: {field}"


class TestNaNProcessingStage:
    """Test NaN Processing Stage"""

    @pytest.fixture
    def nan_stage(self):
        return NaNProcessingStage()

    @pytest.fixture
    def data_with_nans(self):
        return {
            "raw_data": [
                {
                    "symbol": "AAPL",
                    "adapter_id": "test_001",
                    "data": {"price": None, "volume": 1000},
                },
                {
                    "symbol": "GOOGL",
                    "adapter_id": "test_002",
                    "data": {"price": 150.0, "volume": None},
                },
            ]
        }

    @pytest.mark.asyncio
    async def test_nan_processing_replaces_nones(self, nan_stage, data_with_nans):
        """Test that None values are replaced"""
        result = await nan_stage.execute(data_with_nans)

        assert "processed_data" in result
        assert result["nan_stats"]["nan_count"] == 2

        # Check that Nones are replaced with 0
        processed = result["processed_data"]
        assert processed[0]["data"]["price"] == 0
        assert processed[1]["data"]["volume"] == 0

    @pytest.mark.asyncio
    async def test_nan_processing_valid_data(self, nan_stage):
        """Test processing data without NaNs"""
        data = {
            "raw_data": [
                {
                    "symbol": "MSFT",
                    "adapter_id": "test_003",
                    "data": {"price": 200.0, "volume": 5000},
                }
            ]
        }
        result = await nan_stage.execute(data)

        assert result["nan_stats"]["nan_count"] == 0

    @pytest.mark.asyncio
    async def test_nan_processing_invalid_input(self, nan_stage):
        """Test error handling for invalid input"""
        with pytest.raises(ValueError):
            await nan_stage.execute({"raw_data": "not a list"})


class TestTemporalAlignmentStage:
    """Test Temporal Alignment Stage"""

    @pytest.fixture
    def alignment_stage(self):
        return TemporalAlignmentStage()

    @pytest.fixture
    def data_with_timestamps(self):
        return {
            "processed_data": [
                {
                    "symbol": "AAPL",
                    "data": {"timestamp": "2024-01-01T12:00:00"},
                },
                {
                    "symbol": "GOOGL",
                    "data": {"timestamp": datetime(2024, 1, 1, 13, 0, 0)},
                },
            ]
        }

    @pytest.mark.asyncio
    async def test_temporal_alignment_success(
        self, alignment_stage, data_with_timestamps
    ):
        """Test timestamp alignment"""
        result = await alignment_stage.execute(data_with_timestamps)

        assert "aligned_data" in result
        assert result["alignment_stats"]["aligned_count"] == 2

        # Check timestamps are ISO formatted
        for record in result["aligned_data"]:
            assert "timestamp_aligned" in record["data"]
            assert record["data"]["timestamp_aligned"] is True

    @pytest.mark.asyncio
    async def test_temporal_alignment_no_timestamps(self, alignment_stage):
        """Test alignment with no timestamps"""
        data = {"processed_data": [{"symbol": "TSLA", "data": {"price": 150.0}}]}
        result = await alignment_stage.execute(data)

        assert result["alignment_stats"]["aligned_count"] == 0


class TestDeduplicationStage:
    """Test Deduplication Stage"""

    @pytest.fixture
    def dedup_stage(self):
        return DeduplicationStage()

    @pytest.fixture
    def data_with_duplicates(self):
        return {
            "aligned_data": [
                {
                    "adapter_id": "test_001",
                    "symbol": "AAPL",
                    "data": {"timestamp": "2024-01-01T12:00:00", "price": 150.0},
                },
                {
                    "adapter_id": "test_001",
                    "symbol": "AAPL",
                    "data": {"timestamp": "2024-01-01T12:00:00", "price": 150.0},
                },
                {
                    "adapter_id": "test_002",
                    "symbol": "GOOGL",
                    "data": {"timestamp": "2024-01-01T12:00:00", "price": 100.0},
                },
            ]
        }

    @pytest.mark.asyncio
    async def test_deduplication_removes_duplicates(
        self, dedup_stage, data_with_duplicates
    ):
        """Test that duplicates are removed"""
        result = await dedup_stage.execute(data_with_duplicates)

        assert "unique_data" in result
        assert len(result["unique_data"]) == 2
        assert result["dedup_stats"]["duplicates_removed"] == 1

    @pytest.mark.asyncio
    async def test_deduplication_no_duplicates(self, dedup_stage):
        """Test with no duplicates"""
        data = {
            "aligned_data": [
                {
                    "adapter_id": "test_001",
                    "symbol": "AAPL",
                    "data": {"timestamp": "2024-01-01T12:00:00"},
                },
                {
                    "adapter_id": "test_001",
                    "symbol": "AAPL",
                    "data": {"timestamp": "2024-01-01T13:00:00"},
                },
            ]
        }
        result = await dedup_stage.execute(data)

        assert result["dedup_stats"]["duplicates_removed"] == 0
        assert len(result["unique_data"]) == 2


class TestQualityAssuranceStage:
    """Test Quality Assurance Stage"""

    @pytest.fixture
    def qa_stage(self):
        return QualityAssuranceStage()

    @pytest.fixture
    def valid_data(self):
        return {
            "unique_data": [
                {
                    "symbol": "AAPL",
                    "adapter_id": "test_001",
                    "data": {
                        "timestamp": "2024-01-01T12:00:00",
                        "open": 150.0,
                        "close": 152.0,
                        "volume": 1000000,
                    },
                }
            ]
        }

    @pytest.fixture
    def invalid_data(self):
        return {
            "unique_data": [
                {
                    "symbol": "AAPL",
                    "adapter_id": "test_001",
                    "data": {},  # Empty data
                },
                {
                    "symbol": "",  # Missing symbol
                    "adapter_id": "test_002",
                    "data": {"timestamp": "2024-01-01"},
                },
            ]
        }

    @pytest.mark.asyncio
    async def test_qa_valid_data_passes(self, qa_stage, valid_data):
        """Test that valid data passes QA"""
        result = await qa_stage.execute(valid_data)

        assert result["qa_stats"]["qa_passed"] == 1
        assert result["qa_stats"]["qa_failed"] == 0
        assert len(result["validated_data"]) == 1

    @pytest.mark.asyncio
    async def test_qa_invalid_data_fails(self, qa_stage, invalid_data):
        """Test that invalid data fails QA"""
        result = await qa_stage.execute(invalid_data)

        assert result["qa_stats"]["qa_failed"] == 2
        assert result["qa_stats"]["qa_passed"] == 0
        assert len(result["qa_stats"]["issues"]) == 2

    @pytest.mark.asyncio
    async def test_qa_invalid_volume(self, qa_stage):
        """Test detection of negative volume"""
        data = {
            "unique_data": [
                {
                    "symbol": "AAPL",
                    "adapter_id": "test_001",
                    "data": {
                        "timestamp": "2024-01-01",
                        "open": 150.0,
                        "close": 152.0,
                        "volume": -1000,  # Negative volume
                    },
                }
            ]
        }
        result = await qa_stage.execute(data)

        assert result["qa_stats"]["qa_failed"] == 1
        assert any(
            "Negative volume" in str(issue)
            for issue in result["qa_stats"]["issues"][0]["issues"]
        )


class TestDataExportStage:
    """Test Data Export Stage"""

    @pytest.fixture
    def export_stage(self):
        return DataExportStage()

    @pytest.fixture
    def export_data(self, tmp_path):
        return {
            "validated_data": [
                {
                    "symbol": "AAPL",
                    "adapter_id": "test_001",
                    "data": {"price": 150.0},
                }
            ],
            "config": {"output": {"base_dir": str(tmp_path)}},
            "qa_stats": {"qa_passed": 1, "qa_failed": 0},
        }

    @pytest.mark.asyncio
    async def test_export_creates_file(self, export_stage, export_data, tmp_path):
        """Test that export creates output file"""
        result = await export_stage.execute(export_data)

        assert "export_stats" in result
        assert result["export_stats"]["records_exported"] == 1
        assert len(result["export_stats"]["exported_files"]) == 1

        # Check file exists
        import json
        from pathlib import Path

        export_file = Path(result["export_stats"]["exported_files"][0])
        assert export_file.exists()

        # Validate JSON content
        with open(export_file, "r") as f:
            exported = json.load(f)
            assert exported["total_records"] == 1
            assert len(exported["data"]) == 1

    @pytest.mark.asyncio
    async def test_export_empty_data(self, export_stage, tmp_path):
        """Test export with no data"""
        data = {
            "validated_data": [],
            "config": {"output": {"base_dir": str(tmp_path)}},
        }
        result = await export_stage.execute(data)

        assert result["export_stats"]["records_exported"] == 0
