"""
Exporter Tests - Asset-First Structure
Tests the Asset-First export system and unique key deduplication
"""

import pytest
import json
from pathlib import Path
from marketpilot.data_farm.stages.data_export import DataExportStage
from marketpilot.data_farm.stages.deduplication import DeduplicationStage


class TestExporterAssetFirstStructure:
    """Test Asset-First export structure"""

    @pytest.fixture
    def export_stage(self):
        return DataExportStage()

    @pytest.fixture
    def dedup_stage(self):
        return DeduplicationStage()

    @pytest.mark.asyncio
    async def test_asset_first_directory_structure(self, export_stage, tmp_path):
        """Test that export creates Asset-First directory structure"""
        data = {
            "validated_data": [
                {
                    "symbol": "AAPL",
                    "adapter_id": "price_001",
                    "schema_type": "price",
                    "vendor": "yfinance",
                    "data": {
                        "timestamp": "2024-01-01T12:00:00",
                        "open": 150.0,
                        "close": 152.0,
                        "volume": 1000000,
                    },
                    "ingested_at": "2024-01-01T12:00:00",
                },
                {
                    "symbol": "GOOGL",
                    "adapter_id": "price_002",
                    "schema_type": "price",
                    "vendor": "yfinance",
                    "data": {
                        "timestamp": "2024-01-01T12:00:00",
                        "open": 100.0,
                        "close": 104.0,
                        "volume": 500000,
                    },
                    "ingested_at": "2024-01-01T12:00:00",
                },
            ],
            "config": {"output": {"base_dir": str(tmp_path)}},
            "qa_stats": {"qa_passed": 2, "qa_failed": 0},
            "health_check": {},
            "nan_stats": {},
            "alignment_stats": {},
            "dedup_stats": {},
        }

        result = await export_stage.execute(data)

        # Verify structure: base_dir/SYMBOL/schema_type.format
        assert (tmp_path / "AAPL").exists(), "AAPL directory should exist"
        assert (tmp_path / "GOOGL").exists(), "GOOGL directory should exist"

        # Check metadata directory
        assert (tmp_path / "__meta__").exists(), "Metadata directory should exist"

        # Verify export stats
        assert result["export_stats"]["records_exported"] == 2
        assert len(result["export_stats"]["symbols_processed"]) == 2
        assert "AAPL" in result["export_stats"]["symbols_processed"]
        assert "GOOGL" in result["export_stats"]["symbols_processed"]

    @pytest.mark.asyncio
    async def test_multiple_schema_types_per_symbol(self, export_stage, tmp_path):
        """Test exporting multiple schema types for same symbol"""
        data = {
            "validated_data": [
                {
                    "symbol": "AAPL",
                    "adapter_id": "price_001",
                    "schema_type": "price",
                    "vendor": "yfinance",
                    "data": {"timestamp": "2024-01-01", "price": 150.0},
                    "ingested_at": "2024-01-01",
                },
                {
                    "symbol": "AAPL",
                    "adapter_id": "news_001",
                    "schema_type": "news",
                    "vendor": "newsapi",
                    "data": {"startdate": "2024-01-01", "title": "AAPL news"},
                    "ingested_at": "2024-01-01",
                },
                {
                    "symbol": "AAPL",
                    "adapter_id": "fundamental_001",
                    "schema_type": "fundamental",
                    "vendor": "yfinance",
                    "data": {"startdate": "2024-01-01", "pe_ratio": 25.5},
                    "ingested_at": "2024-01-01",
                },
            ],
            "config": {"output": {"base_dir": str(tmp_path)}},
            "qa_stats": {},
            "health_check": {},
            "nan_stats": {},
            "alignment_stats": {},
            "dedup_stats": {},
        }

        result = await export_stage.execute(data)
        print(result)
        # Check AAPL directory has multiple files
        aapl_dir = tmp_path / "AAPL"
        assert aapl_dir.exists()

        files = list(aapl_dir.glob("*"))
        assert (
            len(files) >= 3
        ), "Should have at least 3 files (price, news, fundamental)"

        # Verify all schema types are present
        file_names = [f.stem for f in files]
        assert any("price" in name for name in file_names)
        assert any("news" in name for name in file_names)
        assert any("fundamental" in name for name in file_names)

    @pytest.mark.asyncio
    async def test_exporter_preserves_unique_keys(self, export_stage, tmp_path):
        """Test that exporter only exports unique records"""
        data = {
            "validated_data": [
                {
                    "symbol": "AAPL",
                    "adapter_id": "price_001",
                    "schema_type": "price",
                    "vendor": "yfinance",
                    "data": {
                        "timestamp": "2024-01-01T12:00:00",
                        "price": 150.0,
                    },
                    "ingested_at": "2024-01-01T12:00:00",
                },
                {
                    "symbol": "GOOGL",
                    "adapter_id": "price_002",
                    "schema_type": "price",
                    "vendor": "yfinance",
                    "data": {
                        "timestamp": "2024-01-01T12:00:00",
                        "price": 100.0,
                    },
                    "ingested_at": "2024-01-01T12:00:00",
                },
            ],
            "config": {"output": {"base_dir": str(tmp_path)}},
            "qa_stats": {},
            "health_check": {},
            "nan_stats": {},
            "alignment_stats": {},
            "dedup_stats": {},
        }

        result = await export_stage.execute(data)

        # Read exported files
        aapl_file = tmp_path / "AAPL" / "price.json"
        googl_file = tmp_path / "GOOGL" / "price.json"

        # Check AAPL file
        if aapl_file.exists():
            with open(aapl_file) as f:
                aapl_data = json.load(f)
                assert len(aapl_data) == 1
                assert aapl_data[0]["symbol"] == "AAPL"

        # Check GOOGL file
        if googl_file.exists():
            with open(googl_file) as f:
                googl_data = json.load(f)
                assert len(googl_data) == 1
                assert googl_data[0]["symbol"] == "GOOGL"

        # Verify export stats
        assert result["export_stats"]["records_exported"] == 2

    @pytest.mark.asyncio
    async def test_deduplication_before_export(
        self, dedup_stage, export_stage, tmp_path
    ):
        """Test that deduplication happens before export"""
        # Create data with duplicates
        data_with_duplicates = {
            "aligned_data": [
                {
                    "adapter_id": "price_001",
                    "symbol": "AAPL",
                    "schema_type": "price",
                    "vendor": "yfinance",
                    "data": {"timestamp": "2024-01-01T12:00:00", "price": 150.0},
                    "ingested_at": "2024-01-01",
                },
                {
                    "adapter_id": "price_001",
                    "symbol": "AAPL",
                    "schema_type": "price",
                    "vendor": "yfinance",
                    "data": {
                        "timestamp": "2024-01-01T12:00:00",
                        "price": 150.0,
                    },  # Duplicate
                    "ingested_at": "2024-01-01",
                },
                {
                    "adapter_id": "price_002",
                    "symbol": "GOOGL",
                    "schema_type": "price",
                    "vendor": "yfinance",
                    "data": {"timestamp": "2024-01-01T12:00:00", "price": 100.0},
                    "ingested_at": "2024-01-01",
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
            "health_check": {},
            "nan_stats": {},
            "alignment_stats": {},
        }

        # Run export
        export_result = await export_stage.execute(export_data)

        # Verify only unique records were exported
        assert export_result["export_stats"]["records_exported"] == 2
        assert dedup_result["dedup_stats"]["duplicates_removed"] == 1

    @pytest.mark.asyncio
    async def test_metadata_files_creation(self, export_stage, tmp_path):
        """Test that metadata files are created correctly"""
        data = {
            "validated_data": [
                {
                    "symbol": "AAPL",
                    "adapter_id": "price_001",
                    "schema_type": "price",
                    "vendor": "yfinance",
                    "data": {"timestamp": "2024-01-01", "price": 150.0},
                    "ingested_at": "2024-01-01",
                }
            ],
            "config": {"output": {"base_dir": str(tmp_path)}},
            "health_check": {"total_adapters": 1, "healthy": 1},
            "nan_stats": {"nan_count": 0},
            "alignment_stats": {"aligned_count": 1},
            "dedup_stats": {"duplicates_removed": 0},
            "qa_stats": {"qa_passed": 1, "qa_failed": 0},
        }

        result = await export_stage.execute(data)
        print(result)
        meta_dir = tmp_path / "__meta__"
        assert meta_dir.exists()

        # Check required metadata files
        assert (meta_dir / "schema_versions.yaml").exists()
        assert (meta_dir / "manifest.jsonl").exists()
        assert (meta_dir / "pipeline_stats.json").exists()

        # Validate manifest content
        with open(meta_dir / "manifest.jsonl") as f:
            lines = f.readlines()
            assert len(lines) >= 1

            manifest_entry = json.loads(lines[0])
            assert "symbol" in manifest_entry
            assert "schema_type" in manifest_entry
            assert "record_count" in manifest_entry
            assert manifest_entry["symbol"] == "AAPL"

        # Validate pipeline stats
        with open(meta_dir / "pipeline_stats.json") as f:
            stats = json.load(f)
            assert "pipeline_stats" in stats
            assert "total_symbols" in stats
            assert stats["total_symbols"] == 1

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
    async def test_schema_type_detection_fallback(self, export_stage, tmp_path):
        """Test schema type detection from adapter_id when schema_type missing"""
        data = {
            "validated_data": [
                {
                    "symbol": "AAPL",
                    "adapter_id": "price_yfinance_001",  # Should detect 'price'
                    # schema_type not provided - should fallback to detection
                    "vendor": "yfinance",
                    "data": {"timestamp": "2024-01-01", "price": 150.0},
                    "ingested_at": "2024-01-01",
                },
                {
                    "symbol": "AAPL",
                    "adapter_id": "news_alphavantage_001",  # Should detect 'news'
                    "vendor": "alphavantage",
                    "data": {"startdate": "2024-01-01", "title": "News"},
                    "ingested_at": "2024-01-01",
                },
            ],
            "config": {"output": {"base_dir": str(tmp_path)}},
            "qa_stats": {},
            "health_check": {},
            "nan_stats": {},
            "alignment_stats": {},
            "dedup_stats": {},
        }

        result = await export_stage.execute(data)
        print(result)
        # Check that schema types were detected correctly
        aapl_dir = tmp_path / "AAPL"
        assert aapl_dir.exists()

        files = list(aapl_dir.glob("*"))
        assert len(files) >= 2, "Should have detected both price and news"

    @pytest.mark.asyncio
    async def test_no_timestamp_in_filenames(self, export_stage, tmp_path):
        """Test that filenames don't contain timestamps"""
        data = {
            "validated_data": [
                {
                    "symbol": "AAPL",
                    "adapter_id": "price_001",
                    "schema_type": "price",
                    "vendor": "yfinance",
                    "data": {"timestamp": "2024-01-01", "price": 150.0},
                    "ingested_at": "2024-01-01",
                }
            ],
            "config": {"output": {"base_dir": str(tmp_path)}},
            "qa_stats": {},
            "health_check": {},
            "nan_stats": {},
            "alignment_stats": {},
            "dedup_stats": {},
        }

        result = await export_stage.execute(data)

        # Check that exported files don't have timestamps in names
        exported_files = result["export_stats"]["exported_files"]
        for file_path in exported_files:
            filename = Path(file_path).name
            # Filenames should be like: price.parquet, news.json, etc.
            # NOT like: price_20241101_120000.parquet
            assert not any(
                char.isdigit() for char in filename.split(".")[0]
            ), f"Filename should not contain timestamps: {filename}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
