"""
Additional Exporter Tests - Unique Key Deduplication Logic (MP-010)
Tests the unique key deduplication in the export system
"""

import pytest
import json
from pathlib import Path
from marketpilot.data_farm.stages.data_export import DataExportStage
from marketpilot.data_farm.stages.deduplication import DeduplicationStage


class TestExporterUniqueKeyDeduplication:
    """Test unique key deduplication in exporter"""

    @pytest.fixture
    def export_stage(self):
        return DataExportStage()

    @pytest.fixture
    def dedup_stage(self):
        return DeduplicationStage()

    @pytest.mark.asyncio
    async def test_exporter_preserves_unique_keys(self, export_stage, tmp_path):
        """Test that exporter only exports unique records"""
        data = {
            "validated_data": [
                {
                    "symbol": "AAPL",
                    "adapter_id": "test_001",
                    "data": {
                        "timestamp": "2024-01-01T12:00:00",
                        "price": 150.0,
                    },
                },
                {
                    "symbol": "GOOGL",
                    "adapter_id": "test_002",
                    "data": {
                        "timestamp": "2024-01-01T12:00:00",
                        "price": 100.0,
                    },
                },
            ],
            "config": {"output": {"base_dir": str(tmp_path)}},
            "qa_stats": {},
        }

        result = await export_stage.execute(data)
        export_file = Path(result["export_stats"]["exported_files"][0])

        # Read exported data
        with open(export_file, "r") as f:
            exported = json.load(f)

        # Verify unique records
        exported_data = exported["data"]
        assert len(exported_data) == 2

        # Check each record has unique identifier fields
        keys_seen = set()
        for record in exported_data:
            unique_key = (
                record["symbol"],
                record["adapter_id"],
                record["data"]["timestamp"],
            )
            assert unique_key not in keys_seen, "Duplicate key found in export!"
            keys_seen.add(unique_key)

    @pytest.mark.asyncio
    async def test_deduplication_before_export(
        self, dedup_stage, export_stage, tmp_path
    ):
        """Test that deduplication happens before export"""
        # Create data with duplicates
        data_with_duplicates = {
            "aligned_data": [
                {
                    "adapter_id": "test_001",
                    "symbol": "AAPL",
                    "data": {"timestamp": "2024-01-01T12:00:00", "price": 150.0},
                },
                {
                    "adapter_id": "test_001",
                    "symbol": "AAPL",
                    "data": {
                        "timestamp": "2024-01-01T12:00:00",
                        "price": 150.0,
                    },  # Duplicate
                },
                {
                    "adapter_id": "test_002",
                    "symbol": "GOOGL",
                    "data": {"timestamp": "2024-01-01T12:00:00", "price": 100.0},
                },
            ]
        }

        # Run deduplication
        dedup_result = await dedup_stage.execute(data_with_duplicates)

        # Prepare for export
        export_data = {
            "validated_data": dedup_result["unique_data"],
            "config": {"output": {"base_dir": str(tmp_path)}},
            "dedup_stats": dedup_result["dedup_stats"],
            "qa_stats": {},
        }

        # Run export
        export_result = await export_stage.execute(export_data)

        # Verify only unique records were exported
        assert export_result["export_stats"]["records_exported"] == 2
        assert dedup_result["dedup_stats"]["duplicates_removed"] == 1

    @pytest.mark.asyncio
    async def test_export_schema_validation(self, export_stage, tmp_path):
        """Test exported file has correct schema"""
        data = {
            "validated_data": [
                {
                    "symbol": "AAPL",
                    "adapter_id": "test_001",
                    "data": {"timestamp": "2024-01-01", "price": 150.0},
                }
            ],
            "config": {"output": {"base_dir": str(tmp_path)}},
            "health_check": {"total_adapters": 1},
            "nan_stats": {"nan_count": 0},
            "alignment_stats": {"aligned_count": 1},
            "dedup_stats": {"duplicates_removed": 0},
            "qa_stats": {"qa_passed": 1, "qa_failed": 0},
        }

        result = await export_stage.execute(data)
        export_file = Path(result["export_stats"]["exported_files"][0])

        with open(export_file, "r") as f:
            exported = json.load(f)

        # Validate schema
        required_fields = ["exported_at", "total_records", "pipeline_stats", "data"]
        for field in required_fields:
            assert field in exported, f"Missing field: {field}"

        # Validate pipeline_stats structure
        pipeline_stats = exported["pipeline_stats"]
        stats_fields = [
            "health_check",
            "nan_stats",
            "alignment_stats",
            "dedup_stats",
            "qa_stats",
        ]
        for field in stats_fields:
            assert field in pipeline_stats, f"Missing stats field: {field}"

    @pytest.mark.asyncio
    async def test_export_handles_empty_validated_data(self, export_stage, tmp_path):
        """Test export handles case with no validated data"""
        data = {
            "validated_data": [],
            "config": {"output": {"base_dir": str(tmp_path)}},
        }

        result = await export_stage.execute(data)

        assert result["export_stats"]["records_exported"] == 0
        assert len(result["export_stats"]["exported_files"]) == 0

    @pytest.mark.asyncio
    async def test_unique_key_generation_consistency(self, dedup_stage):
        """Test that unique key generation is consistent"""
        # Same data processed twice should generate same keys
        test_data = {
            "aligned_data": [
                {
                    "adapter_id": "test_001",
                    "symbol": "AAPL",
                    "data": {"timestamp": "2024-01-01T12:00:00"},
                }
            ]
        }

        result1 = await dedup_stage.execute(test_data.copy())
        result2 = await dedup_stage.execute(test_data.copy())

        assert len(result1["unique_data"]) == len(result2["unique_data"])
        assert result1["unique_data"][0] == result2["unique_data"][0]

    @pytest.mark.asyncio
    async def test_export_filename_unique(self, export_stage, tmp_path):
        """Test that each export creates a unique filename"""
        import time

        data = {
            "validated_data": [
                {"symbol": "AAPL", "adapter_id": "test_001", "data": {}}
            ],
            "config": {"output": {"base_dir": str(tmp_path)}},
            "qa_stats": {},
        }

        # First export
        result1 = await export_stage.execute(data)
        file1 = result1["export_stats"]["exported_files"][0]

        time.sleep(1)  # Ensure different timestamp

        # Second export
        result2 = await export_stage.execute(data)
        file2 = result2["export_stats"]["exported_files"][0]

        assert file1 != file2, "Export filenames should be unique"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
