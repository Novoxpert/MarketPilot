"""
Integration Tests for Complete Pipeline
Tests end-to-end pipeline execution
"""

import pytest
from pathlib import Path
from marketpilot.data_farm.resilient_data_farm import ResilientDataFarm


class TestPipelineIntegration:
    """Integration tests for complete data farm pipeline"""

    @pytest.fixture
    async def data_farm(self, tmp_path):
        """Create data farm instance with test config"""
        # Create temporary config
        config_content = f"""
logging:
  level: INFO

output:
  base_dir: {tmp_path}

adapters:
  - id: test_price_001
    type: price
    vendor: yfinance
    cadence: 1min
    schema_type: price

  - id: test_news_001
    type: news
    vendor: alphavantage
    cadence: 15min
    schema_type: news
"""
        config_path = tmp_path / "test_config.yaml"
        config_path.write_text(config_content)

        farm = ResilientDataFarm(str(config_path))
        return farm

    @pytest.mark.asyncio
    async def test_complete_pipeline_execution(self, data_farm):
        """Test complete end-to-end pipeline"""
        symbols = ["AAPL", "GOOGL"]
        result = await data_farm.run_complete_pipeline(symbols)

        # Check all stages completed
        assert "pipeline_start" in result
        assert "pipeline_end" in result
        assert "validated_data" in result

        # Check validation report
        assert "validation_report" in result
        validation = result["validation_report"]
        assert "validation_passed" in validation
        assert len(validation["stages_validated"]) > 0

    @pytest.mark.asyncio
    async def test_smoke_test(self, data_farm):
        """Test smoke test functionality"""
        symbols = ["AAPL"]
        result = await data_farm.run_smoke_test(symbols)

        assert "success" in result
        assert "total_tests" in result
        assert "passed" in result
        assert "failed" in result
        assert len(result["details"]) > 0

    @pytest.mark.asyncio
    async def test_pipeline_with_multiple_symbols(self, data_farm):
        """Test pipeline handles multiple symbols"""
        symbols = ["AAPL", "GOOGL", "MSFT"]
        result = await data_farm.run_complete_pipeline(symbols)

        validated_data = result.get("validated_data", [])
        assert len(validated_data) > 0

        # Check that we have data for multiple symbols
        symbols_found = set(record["symbol"] for record in validated_data)
        assert len(symbols_found) > 1

    @pytest.mark.asyncio
    async def test_pipeline_qa_stats(self, data_farm):
        """Test that QA stats are generated"""
        symbols = ["AAPL"]
        result = await data_farm.run_complete_pipeline(symbols)

        assert "qa_stats" in result
        qa_stats = result["qa_stats"]

        assert "qa_passed" in qa_stats
        assert "qa_failed" in qa_stats
        assert "pass_rate" in qa_stats
        assert "total_records" in qa_stats

    @pytest.mark.asyncio
    async def test_pipeline_export_stats(self, data_farm):
        """Test that export stats are generated"""
        symbols = ["AAPL"]
        result = await data_farm.run_complete_pipeline(symbols)

        assert "export_stats" in result
        export_stats = result["export_stats"]

        assert "exported_files" in export_stats
        assert "records_exported" in export_stats


class TestDataFarmConfiguration:
    """Test data farm configuration and initialization"""

    def test_config_loader_initialization(self):
        """Test that config loader works"""
        from marketpilot.utils.config_loader import load_config

        # This should work with default config
        config = load_config("src/marketpilot/config/data_farm_config.yaml")

        assert "adapters" in config
        assert "logging" in config
        assert "output" in config

    def test_adapter_initialization_from_config(self):
        """Test adapters are initialized from config"""
        farm = ResilientDataFarm()

        adapters = farm.get_adapters()
        assert len(adapters) > 0

        # Check adapter types
        adapter_ids = [a.adapter_id for a in adapters]
        assert any("price" in aid.lower() for aid in adapter_ids)

    def test_get_config_method(self):
        """Test get_config returns loaded configuration"""
        farm = ResilientDataFarm()
        config = farm.get_config()

        assert isinstance(config, dict)
        assert "adapters" in config


class TestErrorHandling:
    """Test error handling in pipeline"""

    @pytest.mark.asyncio
    async def test_pipeline_handles_empty_symbols(self):
        """Test pipeline handles empty symbol list"""
        farm = ResilientDataFarm()
        result = await farm.run_complete_pipeline([])

        # Should complete without error
        assert "validated_data" in result

    @pytest.mark.asyncio
    async def test_pipeline_continues_on_adapter_error(self):
        """Test pipeline continues if one adapter fails"""
        from unittest.mock import patch

        farm = ResilientDataFarm()

        # Mock one adapter to fail
        if farm.adapters:
            with patch.object(
                farm.adapters[0],
                "execute_ingest",
                side_effect=Exception("Simulated failure"),
            ):
                result = await farm.run_complete_pipeline(["AAPL"])

                # Pipeline should still complete
                assert "pipeline_end" in result


class TestLoggingIntegration:
    """Test logging system integration"""

    @pytest.mark.asyncio
    async def test_pipeline_generates_logs(self):
        """Test that pipeline generates log files"""
        farm = ResilientDataFarm()
        await farm.run_smoke_test(["AAPL"])

        # Check that log directories exist
        log_base = Path("logs_test")
        assert (log_base / "pipeline").exists()
        assert (log_base / "adapters").exists()
        assert (log_base / "stages").exists()

    @pytest.mark.asyncio
    async def test_logs_contain_operation_ids(self):
        """Test that logs contain operation IDs"""
        import json

        farm = ResilientDataFarm()
        await farm.run_smoke_test(["AAPL"])

        # Read a log file
        log_file = Path("logs_test/pipeline/current.jsonl")
        if log_file.exists():
            with open(log_file, "r") as f:
                for line in f:
                    entry = json.loads(line)
                    # Check structure
                    assert "timestamp" in entry
                    assert "stage" in entry
                    assert "level" in entry
