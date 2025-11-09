"""
Unit tests for pipeline stages (MP-007)
Tests individual stage functionality
"""

import pytest
from marketpilot.data_farm.stages.health_check import HealthCheckStage
from marketpilot.data_farm.stages.data_collection import DataCollectionStage
from marketpilot.data_farm.stages.nan_processing import NaNProcessingStage
from marketpilot.data_farm.stages.temporal_alignment import TemporalAlignmentStage
from marketpilot.data_farm.stages.deduplication import DeduplicationStage
from marketpilot.data_farm.stages.quality_assurance import QualityAssuranceStage
from marketpilot.data_farm.stages.data_export import DataExportStage


class TestHealthCheckStage:
    """Test Health Check Stage"""

    @pytest.mark.asyncio
    async def test_health_check_with_adapters(self):
        """Test health check with available adapters"""
        stage = HealthCheckStage()
        stage_results = {
            "adapters": [{"adapter_id": "test_adapter"}],
            "config": {"test": "config"},
        }

        stage_results = await stage.execute(stage_results)

        assert "health_check" in stage_results
        assert stage_results["health_check"]["total_adapters"] == 1
        assert stage_results["health_check"]["healthy"] == 1
        assert len(stage_results["health_check"]["details"]) == 1

    @pytest.mark.asyncio
    async def test_health_check_without_adapters(self):
        """Test health check without adapters"""
        stage = HealthCheckStage()
        stage_results = {"adapters": [], "config": {}}

        stage_results = await stage.execute(stage_results)

        assert "health_check" in stage_results
        assert stage_results["health_check"]["total_adapters"] == 0
        assert stage_results["health_check"]["healthy"] == 0


class TestDataCollectionStage:
    """Test Data Collection Stage"""

    @pytest.mark.asyncio
    async def test_data_collection_empty(self):
        """Test data collection with no adapters"""
        stage = DataCollectionStage()
        stage_results = {"adapters": [], "symbols": ["AAPL"]}

        stage_results = await stage.execute(stage_results)

        assert "raw_data" in stage_results
        assert len(stage_results["raw_data"]) == 0


class TestNaNProcessingStage:
    """Test NaN Processing Stage"""

    @pytest.mark.asyncio
    async def test_nan_processing(self):
        """Test NaN processing with sample data"""
        stage = NaNProcessingStage()
        stage_results = {
            "raw_data": [
                {
                    "adapter_id": "test_adapter",
                    "symbol": "AAPL",
                    "data": {"open": 150.0, "close": None},
                }
            ]
        }

        stage_results = await stage.execute(stage_results)

        assert "processed_data" in stage_results
        assert "nan_stats" in stage_results
        assert stage_results["nan_stats"]["nan_count"] >= 0
        # Verify NaN was processed (replaced with 0)
        assert stage_results["processed_data"][0]["data"]["close"] == 0


class TestTemporalAlignmentStage:
    """Test Temporal Alignment Stage"""

    @pytest.mark.asyncio
    async def test_temporal_alignment(self):
        """Test temporal alignment"""
        stage = TemporalAlignmentStage()
        stage_results = {
            "processed_data": [
                {
                    "adapter_id": "test_adapter",
                    "symbol": "AAPL",
                    "data": {"timestamp": "2024-01-01T00:00:00"},
                }
            ]
        }

        stage_results = await stage.execute(stage_results)

        assert "aligned_data" in stage_results
        assert "alignment_stats" in stage_results
        assert stage_results["alignment_stats"]["aligned_count"] == 1
        # Verify timestamp was processed
        assert stage_results["aligned_data"][0]["data"]["timestamp_aligned"] is True


class TestDeduplicationStage:
    """Test Deduplication Stage"""

    @pytest.mark.asyncio
    async def test_deduplication(self):
        """Test deduplication removes duplicates"""
        stage = DeduplicationStage()
        stage_results = {
            "aligned_data": [
                {
                    "adapter_id": "test_1",
                    "symbol": "AAPL",
                    "data": {"timestamp": "2024-01-01T00:00:00"},
                },
                {
                    "adapter_id": "test_1",
                    "symbol": "AAPL",
                    "data": {"timestamp": "2024-01-01T00:00:00"},
                },
            ]
        }

        stage_results = await stage.execute(stage_results)

        assert "unique_data" in stage_results
        assert "dedup_stats" in stage_results
        assert stage_results["dedup_stats"]["duplicates_removed"] == 1
        assert len(stage_results["unique_data"]) == 1


class TestQualityAssuranceStage:
    """Test Quality Assurance Stage"""

    @pytest.mark.asyncio
    async def test_qa_validation(self):
        """Test QA validates data correctly"""
        stage = QualityAssuranceStage()
        stage_results = {
            "unique_data": [
                {
                    "adapter_id": "test_adapter",
                    "symbol": "AAPL",
                    "data": {
                        "symbol": "AAPL",
                        "timestamp": "2024-01-01T00:00:00",
                        "open": 150.0,
                        "close": 152.0,
                    },
                }
            ]
        }

        stage_results = await stage.execute(stage_results)

        assert "validated_data" in stage_results
        assert "qa_stats" in stage_results
        assert stage_results["qa_stats"]["qa_passed"] == 1
        assert stage_results["qa_stats"]["qa_failed"] == 0
        assert len(stage_results["validated_data"]) == 1


class TestDataExportStage:
    """Test Data Export Stage"""

    @pytest.mark.asyncio
    async def test_data_export_empty(self):
        """Test export with no data"""
        stage = DataExportStage()
        stage_results = {
            "config": {},
            "validated_data": [],
        }

        stage_results = await stage.execute(stage_results)

        assert "export_stats" in stage_results
        assert stage_results["export_stats"]["records_exported"] == 0
        assert len(stage_results["export_stats"]["exported_files"]) == 0


# Run tests
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
