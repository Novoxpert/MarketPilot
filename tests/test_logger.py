"""
Clean and stable Unit Tests for Mode-Aware Logger
"""

import json
from datetime import datetime
import pytest

from marketpilot.utils.logger import log_event
from marketpilot.utils.mode_manager import get_mode_manager


class TestLogger:
    """Test logging functionality"""

    # ---------------------------------------------------------
    def test_log_directory_creation(self):
        """Ensure that base log directories exist"""
        manager = get_mode_manager()
        log_base = manager.get_log_dir()

        assert (log_base / "pipeline").exists()
        assert (log_base / "stages").exists()
        assert (log_base / "adapters").exists()
        assert (log_base / "errors").exists()

    # ---------------------------------------------------------
    def test_log_event_writes_to_file(self):
        """Ensure log_event writes files"""

        log_event(
            stage="test",
            block="test_block",
            level="INFO",
            msg="Test message",
            extra={"test_field": "test_value"},
        )

        manager = get_mode_manager()
        log_files = list(manager.get_log_dir().rglob("*.jsonl"))

        assert len(log_files) > 0, "No log file created"

    # ---------------------------------------------------------
    def test_log_entry_format(self):
        """Ensure log entry JSON format is correct"""

        test_msg = f"Format test at {datetime.utcnow().isoformat()}"

        log_event(
            stage="test_format",
            block="test_block",
            level="INFO",
            msg=test_msg,
            extra={"custom_field": "custom_value"},
        )

        manager = get_mode_manager()
        log_files = list(manager.get_log_dir().rglob("*.jsonl"))

        found = False
        for file in log_files:
            with open(file, "r") as f:
                for line in f:
                    entry = json.loads(line)
                    if entry.get("message") == test_msg:
                        assert entry["stage"] == "test_format"
                        assert entry["block"] == "test_block"
                        assert entry["level"] == "INFO"
                        assert entry["custom_field"] == "custom_value"
                        assert "timestamp" in entry
                        found = True
                        break

        assert found, "Log entry with correct format not found"

    # ---------------------------------------------------------
    def test_error_log(self):
        """Ensure ERROR logs go to errors directory"""

        log_event(
            stage="test",
            block="test_block",
            level="ERROR",
            msg="Test error",
            extra={"error_type": "TestError"},
        )

        manager = get_mode_manager()
        error_file = manager.get_log_dir() / "errors" / "current.jsonl"

        assert error_file.exists(), "ERROR log file missing"

        with open(error_file) as f:
            has_error = any(json.loads(line).get("level") == "ERROR" for line in f)

        assert has_error, "No ERROR entry inside errors log"

    # ---------------------------------------------------------
    def test_adapter_log(self):
        """Ensure adapter logs go to adapters/ directory"""

        log_event(
            stage="ingestion",
            block="yfinance_adapter",
            level="INFO",
            msg="Test adapter log",
        )

        manager = get_mode_manager()
        adapter_dir = manager.get_log_dir() / "adapters"

        assert adapter_dir.exists()
        assert len(list(adapter_dir.glob("*.jsonl"))) > 0

    # ---------------------------------------------------------
    def test_stage_log(self):
        """Ensure stage logs go to stages/ directory"""

        log_event(
            stage="data_collection",
            block="stage",
            level="INFO",
            msg="Test stage log",
        )

        manager = get_mode_manager()
        stage_dir = manager.get_log_dir() / "stages"

        assert stage_dir.exists()
        assert len(list(stage_dir.glob("*.jsonl"))) > 0

    # ---------------------------------------------------------
    def test_log_levels(self):
        """Ensure all log levels are accepted"""

        levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]

        for level in levels:
            log_event(
                stage="test",
                block="test_block",
                level=level,
                msg=f"Test {level} message",
            )

        manager = get_mode_manager()
        assert len(list(manager.get_log_dir().rglob("*.jsonl"))) > 0

    # ---------------------------------------------------------
    def test_extra_fields_in_logs(self):
        """Ensure extra fields persist"""

        extra = {"symbol": "AAPL", "price": 150.5, "volume": 123456}
        test_msg = f"Extra field test at {datetime.utcnow().isoformat()}"

        log_event(
            stage="test_extra",
            block="test_block",
            level="INFO",
            msg=test_msg,
            extra=extra,
        )

        manager = get_mode_manager()
        log_files = list(manager.get_log_dir().rglob("*.jsonl"))

        found = False
        for file in log_files:
            with open(file, "r") as f:
                for line in f:
                    entry = json.loads(line)
                    if entry.get("message") == test_msg:
                        for key, value in extra.items():
                            assert entry.get(key) == value
                        found = True
                        break

        assert found, "Extra field log entry not found"

    # ---------------------------------------------------------
    def test_test_mode_indicator(self):
        """Ensure test mode adds indicator field"""

        manager = get_mode_manager()
        test_msg = f"Test mode indicator at {datetime.utcnow().isoformat()}"

        log_event(
            stage="test_mode_check",
            block="test_block",
            level="INFO",
            msg=test_msg,
        )

        log_files = list(manager.get_log_dir().rglob("*.jsonl"))

        found = False
        for fpath in log_files:
            with open(fpath) as f:
                for line in f:
                    entry = json.loads(line)
                    if entry.get("message") == test_msg:
                        if manager.is_test_mode:
                            assert entry.get("test_mode") is True
                        found = True
                        break

        assert found, "Test mode log entry not found"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
