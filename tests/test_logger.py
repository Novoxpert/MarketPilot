"""
Unit Tests for Logger - Updated for Mode-Aware Logger
✅ No duplicate setup_logging calls - handled by conftest.py
"""

import pytest
import json
from datetime import datetime
from marketpilot.utils.logger import log_event  # ✅ حذف setup_logging
from marketpilot.utils.mode_manager import get_mode_manager


class TestLogger:
    """Test logging functionality"""

    def test_log_directory_creation(self):
        """Test that log directories are created"""
        # ✅ حذف setup_logging() - conftest.py اینو انجام میده

        manager = get_mode_manager()
        log_base = manager.get_log_dir()

        # Check that base directories exist
        assert (log_base / "pipeline").exists()
        assert (log_base / "stages").exists()
        assert (log_base / "adapters").exists()
        assert (log_base / "errors").exists()

    def test_log_event_writes_to_file(self):
        """Test that log events are written to files"""
        # ✅ حذف setup_logging()

        log_event(
            stage="test",
            block="test_block",
            level="INFO",
            msg="Test message",
            extra={"test_field": "test_value"},
        )

        # Check that log file exists
        manager = get_mode_manager()
        log_base = manager.get_log_dir()
        log_files = list(log_base.rglob("*.jsonl"))

        assert len(log_files) > 0, "At least one log file should exist"

    def test_log_entry_format(self):
        """Test that log entries have correct format"""
        # Use unique message to find our entry
        test_msg = f"Test message at {datetime.now().isoformat()}"

        # ✅ حذف setup_logging()

        log_event(
            stage="test_format",
            block="test_block",
            level="INFO",
            msg=test_msg,
            extra={"custom_field": "custom_value"},
        )

        # Find and read log file
        manager = get_mode_manager()
        log_base = manager.get_log_dir()
        log_files = list(log_base.rglob("*.jsonl"))

        assert len(log_files) > 0

        # Find our entry
        found = False
        for log_file in log_files:
            with open(log_file, "r", encoding="utf-8") as f:
                for line in f:
                    entry = json.loads(line)
                    if entry.get("message") == test_msg:
                        # Check required fields
                        assert "timestamp" in entry
                        assert "stage" in entry
                        assert "block" in entry
                        assert "level" in entry
                        assert "message" in entry
                        assert "custom_field" in entry
                        assert entry["custom_field"] == "custom_value"
                        found = True
                        break
            if found:
                break

        assert found, f"Could not find log entry with message: {test_msg}"

    def test_error_log_routing(self):
        """Test that errors go to errors directory"""
        # ✅ حذف setup_logging()

        log_event(
            stage="test",
            block="test_block",
            level="ERROR",
            msg="Test error",
            extra={"error_type": "TestError"},
        )

        # Check errors directory
        manager = get_mode_manager()
        error_log = manager.get_log_dir() / "errors" / "current.jsonl"

        assert error_log.exists(), "Error log should exist"

        # Verify content
        with open(error_log, "r") as f:
            lines = f.readlines()
            # Find an error entry
            found_error = False
            for line in lines:
                entry = json.loads(line)
                if entry.get("level") == "ERROR":
                    found_error = True
                    break
            assert found_error, "Should have at least one ERROR entry"

    def test_adapter_log_routing(self):
        """Test that adapter logs go to adapters directory"""
        # ✅ حذف setup_logging()

        log_event(
            stage="ingestion",
            block="yfinance_adapter",
            level="INFO",
            msg="Test adapter log",
        )

        # Check adapters directory
        manager = get_mode_manager()
        adapter_dir = manager.get_log_dir() / "adapters"

        assert adapter_dir.exists()
        log_files = list(adapter_dir.glob("*.jsonl"))
        assert len(log_files) > 0

    def test_stage_log_routing(self):
        """Test that stage logs go to stages directory"""
        # ✅ حذف setup_logging()

        log_event(
            stage="data_collection", block="stage", level="INFO", msg="Test stage log"
        )

        # Check stages directory
        manager = get_mode_manager()
        stage_dir = manager.get_log_dir() / "stages"

        assert stage_dir.exists()
        log_files = list(stage_dir.glob("*.jsonl"))
        assert len(log_files) > 0

    def test_log_levels(self):
        """Test different log levels"""
        # ✅ حذف setup_logging("DEBUG")
        # Note: Log level is set to INFO in conftest.py
        # If you need DEBUG level, you can still log DEBUG messages

        levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]

        for level in levels:
            log_event(
                stage="test",
                block="test_block",
                level=level,
                msg=f"Test {level} message",
            )

        # Verify at least one log file exists
        manager = get_mode_manager()
        log_files = list(manager.get_log_dir().rglob("*.jsonl"))
        assert len(log_files) > 0

    def test_extra_fields_in_logs(self):
        """Test that extra fields are preserved"""
        # Use unique message to find our entry
        test_msg = f"Test with extra data at {datetime.now().isoformat()}"

        # ✅ حذف setup_logging()

        extra_data = {"symbol": "AAPL", "price": 150.0, "volume": 1000000}

        log_event(
            stage="test_extra",
            block="test_extra_block",
            level="INFO",
            msg=test_msg,
            extra=extra_data,
        )

        # Read log and verify
        manager = get_mode_manager()
        log_files = list(manager.get_log_dir().rglob("*.jsonl"))

        # Find our entry
        found = False
        for log_file in log_files:
            with open(log_file, "r") as f:
                for line in f:
                    entry = json.loads(line)
                    if entry.get("message") == test_msg:
                        # Verify extra fields
                        for key, value in extra_data.items():
                            assert key in entry, f"Field {key} not found in log entry"
                            assert entry[key] == value, f"Field {key} value mismatch"
                        found = True
                        break
            if found:
                break

        assert found, f"Could not find log entry with message: {test_msg}"

    def test_test_mode_indicator(self):
        """Test that test mode adds indicator to logs"""
        # ✅ حذف set_test_mode() - conftest.py already did this
        # ✅ حذف setup_logging()

        manager = get_mode_manager()
        test_msg = f"Test mode message at {datetime.now().isoformat()}"

        log_event(
            stage="test_mode_check", block="test_block", level="INFO", msg=test_msg
        )

        # Read log and check for test_mode field
        log_files = list(manager.get_log_dir().rglob("*.jsonl"))

        found = False
        for log_file in log_files:
            with open(log_file, "r") as f:
                for line in f:
                    entry = json.loads(line)
                    if entry.get("message") == test_msg:
                        if manager.is_test_mode:
                            assert "test_mode" in entry
                            assert entry["test_mode"] is True
                        found = True
                        break
            if found:
                break

        assert found, f"Could not find log entry with message: {test_msg}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
