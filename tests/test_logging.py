"""
Unit Tests for Enhanced Logging
 Now mode-aware - works in both test and normal mode
"""

import pytest
import json
from datetime import datetime
from marketpilot.utils.logger import log_event
from marketpilot.utils.log_validator import LogValidator
from marketpilot.utils.mode_manager import (
    get_mode_manager,
    set_test_mode,
    set_normal_mode,
    reset_mode,
    is_test_mode,
    AppMode,
)


class TestLoggingEnhancements:
    def test_log_event_basic_structure(self):
        """Test that log events have basic structure"""
        log_event(
            stage="test_stage",
            block="test_block",
            level="INFO",
            msg="Test message",
            extra={"test_field": "test_value"},
        )

        #  Use mode-aware log directory
        manager = get_mode_manager()
        log_dir = manager.get_log_dir()
        assert log_dir.exists(), f"Log directory should exist at {log_dir}"

        # Find most recent log file
        log_files = list(log_dir.rglob("*.jsonl"))
        assert len(log_files) > 0, "At least one log file should exist"

    def test_log_event_with_metrics(self):
        """Test logging with performance metrics"""
        log_event(
            stage="test_stage",
            block="test_block",
            level="INFO",
            msg="Completed operation",
            extra={
                "operation_id": "test123",
                "duration_ms": 150.5,
                "records_processed": 10,
                "success_flag": True,
            },
        )

        #  Use mode-aware log directory
        manager = get_mode_manager()
        log_files = list(manager.get_log_dir().rglob("*.jsonl"))
        assert len(log_files) > 0

    def test_error_log(self):
        """Test that errors are logged to error directory"""
        log_event(
            stage="test_stage",
            block="test_block",
            level="ERROR",
            msg="Test error message",
            extra={"error_type": "TestError", "error_message": "Test error"},
        )

        #  Use mode-aware error log path
        manager = get_mode_manager()
        error_log = manager.get_log_dir() / "errors" / "current.jsonl"
        assert error_log.exists(), f"Error log file should exist at {error_log}"

        # Verify it contains the error
        with open(error_log, "r", encoding="utf-8") as f:
            lines = f.readlines()
            assert len(lines) > 0, "Error log should have entries"

            # Check last entry is our error
            last_entry = json.loads(lines[-1])
            assert last_entry["level"] == "ERROR"
            assert "error_type" in last_entry

    def test_adapter_log(self):
        """Test that adapter logs go to correct directory"""
        log_event(
            stage="ingestion",
            block="yfinance_adapter",
            level="INFO",
            msg="Test adapter log",
            extra={"adapter_id": "price_001"},
        )

        #  Use mode-aware adapter log path
        manager = get_mode_manager()
        adapter_log = manager.get_log_dir() / "adapters"
        assert (
            adapter_log.exists()
        ), f"Adapter log directory should exist at {adapter_log}"

    def test_stage_log(self):
        """Test that stage logs go to correct directory"""
        log_event(
            stage="data_collection",
            block="stage",
            level="INFO",
            msg="Test stage log",
            extra={"operation_id": "test456"},
        )

        #  Use mode-aware stage log path
        manager = get_mode_manager()
        stage_log = manager.get_log_dir() / "stages"
        assert stage_log.exists(), f"Stage log directory should exist at {stage_log}"


class TestLogValidator:
    """Test JSONL log validation"""

    def test_validate_valid_log_entry(self):
        """Test validation of valid log entry"""
        valid_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "stage": "test_stage",
            "block": "test_block",
            "level": "INFO",
            "message": "Test message",
        }

        result = LogValidator._validate_entry(valid_entry, 1)
        assert len(result["missing_fields"]) == 0
        assert result["invalid_level"] is False
        assert len(result.get("schema_errors", [])) == 0

    def test_validate_against_schema(self):
        """Test JSON schema validation"""
        valid_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "stage": "test",
            "block": "test",
            "level": "INFO",
            "message": "Test",
        }

        errors = LogValidator.validate_against_schema(
            valid_entry, LogValidator.LOG_ENTRY_SCHEMA
        )
        assert len(errors) == 0, "Valid entry should pass schema validation"

    def test_schema_validation_invalid_type(self):
        """Test schema validation catches type errors"""
        invalid_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "stage": "test",
            "block": "test",
            "level": 123,  #  Should be string
            "message": "Test",
        }

        errors = LogValidator.validate_against_schema(
            invalid_entry, LogValidator.LOG_ENTRY_SCHEMA
        )
        assert len(errors) > 0, "Should detect type error"

    def test_validate_missing_fields(self):
        """Test detection of missing required fields"""
        invalid_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "stage": "test_stage",
            # Missing: block, level, message
        }

        result = LogValidator._validate_entry(invalid_entry, 1)
        assert len(result["missing_fields"]) > 0
        assert "block" in result["missing_fields"]
        assert "level" in result["missing_fields"]
        assert "message" in result["missing_fields"]

    def test_validate_invalid_log_level(self):
        """Test detection of invalid log level"""
        invalid_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "stage": "test_stage",
            "block": "test_block",
            "level": "INVALID_LEVEL",
            "message": "Test",
        }

        result = LogValidator._validate_entry(invalid_entry, 1)
        assert result["invalid_level"] is True

    def test_validate_stage_log_metrics(self):
        """Test validation of stage-specific metrics"""
        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "stage": "test_stage",
            "block": "stage",
            "level": "INFO",
            "message": "Completed test_stage",
            "extra": {
                "operation_id": "test123",
                "duration_ms": 100.5,
                "records_processed": 5,
                "success_flag": True,
            },
        }

        missing = LogValidator.validate_stage_logs(log_entry)
        assert len(missing) == 0, "All required metrics should be present"

    def test_validate_stage_log_missing_metrics(self):
        """Test detection of missing stage metrics"""
        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "stage": "test_stage",
            "block": "stage",
            "level": "INFO",
            "message": "Completed test_stage",
            "extra": {
                # Missing: operation_id, duration_ms, success_flag
                "records_processed": 5,
            },
        }

        missing = LogValidator.validate_stage_logs(log_entry)
        assert len(missing) > 0
        assert "operation_id" in missing
        assert "duration_ms" in missing
        assert "success_flag" in missing

    def test_validate_log_file_format(self):
        """Test validation of entire log file"""
        #  Use mode-aware log directory
        manager = get_mode_manager()
        test_log = manager.get_log_dir() / "test_validation.jsonl"
        test_log.parent.mkdir(parents=True, exist_ok=True)

        with open(test_log, "w", encoding="utf-8") as f:
            # Valid entry
            valid_entry = {
                "timestamp": datetime.utcnow().isoformat(),
                "stage": "test",
                "block": "test",
                "level": "INFO",
                "message": "Test",
            }
            f.write(json.dumps(valid_entry) + "\n")

            # Another valid entry
            f.write(json.dumps(valid_entry) + "\n")

        # Validate
        validator = LogValidator()
        report = validator.validate_log_file(test_log)

        assert report["valid"] is True
        assert report["total_entries"] == 2
        assert len(report["malformed_entries"]) == 0

        # Cleanup
        test_log.unlink()

    def test_validate_malformed_log_entry(self):
        """Test detection of malformed JSON"""
        #  Use mode-aware log directory
        manager = get_mode_manager()
        test_log = manager.get_log_dir() / "test_malformed.jsonl"
        test_log.parent.mkdir(parents=True, exist_ok=True)

        with open(test_log, "w", encoding="utf-8") as f:
            # Valid entry
            valid_entry = {
                "timestamp": datetime.utcnow().isoformat(),
                "stage": "test",
                "block": "test",
                "level": "INFO",
                "message": "Test",
            }
            f.write(json.dumps(valid_entry) + "\n")

            # Malformed entry (invalid JSON)
            f.write("{'invalid': json syntax}\n")

        # Validate
        validator = LogValidator()
        report = validator.validate_log_file(test_log)

        assert report["valid"] is False
        assert len(report["malformed_entries"]) == 1
        assert report["total_entries"] == 1  # Only counts valid entries

        # Cleanup
        test_log.unlink()


class TestIntegratedLogging:
    """Test integrated logging across stages and adapters"""

    @pytest.mark.asyncio
    async def test_stage_logging_integration(self):
        """Test that stages log correctly"""
        from marketpilot.data_farm.stages.health_check import HealthCheckStage
        from marketpilot.utils.mode_manager import get_mode_manager
        import os

        stage = HealthCheckStage()

        # Execute stage with mock data
        data = {"adapters": [], "symbols": ["AAPL"]}
        result = await stage.execute(data)
        print("Stage result:", result)

        # Mode-aware log directory
        manager = get_mode_manager()
        log_dir = manager.get_log_dir() / "stages"
        assert log_dir.exists(), f"Stages log directory does not exist: {log_dir}"

        log_file = log_dir / "stages.jsonl"

        if not log_file.exists():
            log_files = list(log_dir.glob("*.jsonl"))
            assert (
                len(log_files) > 0
            ), f"No stage log file exists in directory: {log_dir}"

            # Sort by modification time (newest first)
            log_files.sort(key=os.path.getmtime, reverse=True)
            log_file = log_files[0]

        assert log_file.exists(), f"Stage log file not found: {log_file}"

        # Read log lines
        with open(log_file, "r", encoding="utf-8") as f:
            lines = f.readlines()

        assert len(lines) > 0, "Stage log file is empty"

        # Look only at last few lines
        recent_lines = lines[-10:]

        completion_log_found = False

        for line in reversed(recent_lines):
            try:
                entry = json.loads(line)
            except json.JSONDecodeError:
                continue

            # Match final completion log for health_check stage
            if entry.get("stage") == "health_check" and "Completed" in entry.get(
                "message", ""
            ):
                required_fields = ["operation_id", "duration_ms", "success_flag"]

                # All must be in root of log entry
                if all(key in entry for key in required_fields):
                    # Type validation
                    assert isinstance(entry["operation_id"], str)
                    assert isinstance(entry["duration_ms"], (int, float))
                    assert isinstance(entry["success_flag"], bool)
                    assert entry["success_flag"] is True

                    completion_log_found = True
                    break

        if not completion_log_found:
            # Debug printing of last log lines
            print("\n DEBUG — Recent log entries:")
            for line in recent_lines:
                try:
                    parsed = json.loads(line)
                    print(
                        f"  Stage={parsed.get('stage')} | "
                        f"Message={parsed.get('message')} | "
                        f"Keys={list(parsed.keys())}"
                    )
                except Exception as e:
                    print(f"Recent log entries: {str(e)}")
                    print(" Malformed:", line.strip())

            pytest.fail(
                "Enhanced completion log not found. "
                "Fields must be in root: operation_id, duration_ms, success_flag"
            )

        assert completion_log_found, "Did not detect enhanced completion log entry"


# mode manager tests


class TestModeManager:
    """Comprehensive tests for mode manager"""

    def test_mode_manager_singleton(self):
        """Test mode manager is singleton"""
        manager1 = get_mode_manager()
        manager2 = get_mode_manager()
        assert manager1 is manager2

    def test_mode_manager_initial_mode(self):
        """Test initial mode is captured correctly"""
        # Reset to ensure clean state
        reset_mode()

        manager = get_mode_manager()

        # The current mode should match the initial mode after reset
        assert manager.mode == manager._instance._initial_mode

        # Initial mode should be either NORMAL or TEST depending on environment
        assert manager._instance._initial_mode in [AppMode.NORMAL, AppMode.TEST]

    def test_mode_manager_set_test_mode(self):
        """Test setting test mode"""
        set_test_mode()
        assert is_test_mode() is True

        manager = get_mode_manager()
        assert manager.is_test_mode is True
        assert manager.is_normal_mode is False

        reset_mode()

    def test_mode_manager_set_normal_mode(self):
        """Test setting normal mode"""
        set_normal_mode()
        manager = get_mode_manager()
        assert manager.is_normal_mode is True
        assert manager.is_test_mode is False

    def test_mode_manager_reset_mode(self):
        """Test reset mode"""
        set_test_mode()
        reset_mode()
        # Should return to initial mode

    def test_mode_manager_get_log_dir(self):
        """Test get_log_dir based on mode"""
        set_test_mode()
        manager = get_mode_manager()
        assert str(manager.get_log_dir()) == "logs_test"

        set_normal_mode()
        assert str(manager.get_log_dir()) == "logs"

        reset_mode()

    def test_mode_manager_get_data_dir(self):
        """Test get_data_dir based on mode"""
        set_test_mode()
        manager = get_mode_manager()
        assert str(manager.get_data_dir()) == "data_test"

        set_normal_mode()
        assert str(manager.get_data_dir()) == "data"

        reset_mode()

    def test_mode_manager_get_config_file(self):
        """Test get_config_file"""
        manager = get_mode_manager()
        config = manager.get_config_file()
        assert "data_farm_config.yaml" in str(config)

    def test_mode_manager_get_db_name(self):
        """Test get_db_name"""
        set_test_mode()
        manager = get_mode_manager()
        assert manager.get_db_name() == "marketpilot_test"

        set_normal_mode()
        assert manager.get_db_name() == "marketpilot"

        reset_mode()

    def test_mode_manager_get_env_prefix(self):
        """Test get_env_prefix"""
        set_test_mode()
        manager = get_mode_manager()
        assert manager.get_env_prefix() == "TEST_"

        set_normal_mode()
        assert manager.get_env_prefix() == ""

        reset_mode()

    def test_mode_manager_get_all_paths(self):
        """Test get_all_paths"""
        manager = get_mode_manager()
        paths = manager.get_all_paths()

        assert "log_dir" in paths
        assert "data_dir" in paths
        assert "config_file" in paths
        assert "output_dir" in paths

    def test_mode_manager_repr(self):
        """Test __repr__ method"""
        manager = get_mode_manager()
        repr_str = repr(manager)
        assert "ModeManager" in repr_str


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
