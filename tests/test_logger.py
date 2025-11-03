"""Story MP-003
Unit tests for centralized logging system
Run with: pytest tests/test_logger.py
"""

import json
import pytest
from datetime import datetime
from marketpilot.utils.logger import log_event, setup_logging, LOG_DIRS


@pytest.fixture
def clean_logs():
    """Clean up log files before and after tests"""
    # Setup: create directories
    for log_dir in LOG_DIRS.values():
        log_dir.mkdir(parents=True, exist_ok=True)

    yield

    # Teardown: clean test logs (optional, comment out to inspect logs)
    # for log_dir in LOG_DIRS.values():
    #     for log_file in log_dir.glob("*.jsonl"):
    #         log_file.unlink()


def test_log_directories_created(clean_logs):
    """Test that log directories are created"""
    setup_logging()

    for log_dir in LOG_DIRS.values():
        assert log_dir.exists(), f"Log directory {log_dir} was not created"


def test_adapter_log_written(clean_logs):
    """Test adapter logs are written to correct directory"""
    setup_logging()

    log_event(
        stage="ingestion",
        block="alphavantage_adapter",
        level="INFO",
        msg="Test adapter log",
        extra={"symbol": "AAPL"},
    )

    # Check that log file exists
    adapter_logs = list(LOG_DIRS["adapters"].glob("*.jsonl"))
    assert len(adapter_logs) > 0, "No adapter log files created"

    # Read and verify log content
    with open(adapter_logs[0], "r") as f:
        lines = f.readlines()
        assert len(lines) > 0, "Log file is empty"

        log_entry = json.loads(lines[-1])
        assert log_entry["stage"] == "ingestion"
        assert log_entry["block"] == "alphavantage_adapter"
        assert log_entry["level"] == "INFO"
        assert log_entry["message"] == "Test adapter log"
        assert log_entry["symbol"] == "AAPL"
        assert "timestamp" in log_entry


def test_stage_log_written(clean_logs):
    """Test stage logs are written to correct directory"""
    setup_logging()

    log_event(
        stage="quality",
        block="price_validator_stage",
        level="WARNING",
        msg="Test stage log",
        extra={"warnings": 3},
    )

    # Check that log file exists
    stage_logs = list(LOG_DIRS["stages"].glob("*.jsonl"))
    assert len(stage_logs) > 0, "No stage log files created"

    # Verify log content
    with open(stage_logs[0], "r") as f:
        lines = f.readlines()
        log_entry = json.loads(lines[-1])
        assert log_entry["stage"] == "quality"
        assert log_entry["level"] == "WARNING"


def test_error_log_written(clean_logs):
    """Test error logs are written to errors directory"""
    setup_logging()

    log_event(
        stage="ingestion",
        block="fmp_adapter",
        level="ERROR",
        msg="Test error log",
        extra={"error_code": 500},
    )

    # Check that log file exists in errors directory
    error_logs = list(LOG_DIRS["errors"].glob("*.jsonl"))
    assert len(error_logs) > 0, "No error log files created"

    # Verify log content
    with open(error_logs[0], "r") as f:
        lines = f.readlines()
        log_entry = json.loads(lines[-1])
        assert log_entry["level"] == "ERROR"
        assert log_entry["error_code"] == 500


def test_jsonl_format_parsable(clean_logs):
    """Test that all log entries are valid JSON"""
    setup_logging()

    # Write multiple log entries
    for i in range(5):
        log_event(
            stage="test",
            block="test_component",
            level="INFO",
            msg=f"Test message {i}",
            extra={"iteration": i},
        )

    # Read and parse all lines
    pipeline_logs = list(LOG_DIRS["pipeline"].glob("*.jsonl"))
    assert len(pipeline_logs) > 0

    with open(pipeline_logs[0], "r") as f:
        for line in f:
            # Should not raise exception
            log_entry = json.loads(line.strip())
            assert "timestamp" in log_entry
            assert "stage" in log_entry
            assert "block" in log_entry
            assert "level" in log_entry
            assert "message" in log_entry


def test_log_rotation_by_date(clean_logs):
    """Test that logs use date-based file names"""
    setup_logging()

    log_event("test", "test_block", "INFO", "Test message")

    today = datetime.now().strftime("%Y%m%d")

    # Check that filename contains today's date
    for log_dir in LOG_DIRS.values():
        log_files = list(log_dir.glob("*.jsonl"))
        if log_files:
            for log_file in log_files:
                assert (
                    today in log_file.name
                ), f"Log file {log_file.name} doesn't contain date"


def test_extra_fields_preserved(clean_logs):
    """Test that extra fields are correctly added to logs"""
    setup_logging()

    extra_data = {
        "symbol": "AAPL",
        "records": 100,
        "api_version": "v2",
        "response_time": 1.23,
    }

    log_event(
        stage="ingestion",
        block="test_adapter",
        level="INFO",
        msg="Test with extra fields",
        extra=extra_data,
    )

    adapter_logs = list(LOG_DIRS["adapters"].glob("*.jsonl"))
    with open(adapter_logs[0], "r") as f:
        lines = f.readlines()
        log_entry = json.loads(lines[-1])

        for key, value in extra_data.items():
            assert log_entry[key] == value, f"Extra field {key} not preserved correctly"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
