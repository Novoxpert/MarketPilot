"""
Unit Tests for Enhanced Logging
"""

import pytest
import json
from datetime import datetime
from marketpilot.utils.logger import log_event  # ✅ حذف setup_logging
from marketpilot.utils.log_validator import LogValidator
from marketpilot.utils.mode_manager import get_mode_manager


class TestLoggingEnhancements:
    """Test enhanced logging functionality"""

    # ✅ No setup fixture needed - conftest.py handles everything

    def test_log_event_basic_structure(self):
        """Test that log events have basic structure"""
        log_event(
            stage="test_stage",
            block="test_block",
            level="INFO",
            msg="Test message",
            extra={"test_field": "test_value"},
        )

        # ✅ Use mode-aware log directory
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

        # ✅ Use mode-aware log directory
        manager = get_mode_manager()
        log_files = list(manager.get_log_dir().rglob("*.jsonl"))
        assert len(log_files) > 0

    def test_error_log_routing(self):
        """Test that errors are logged to error directory"""
        log_event(
            stage="test_stage",
            block="test_block",
            level="ERROR",
            msg="Test error message",
            extra={"error_type": "TestError", "error_message": "Test error"},
        )

        # ✅ Use mode-aware error log path
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

    def test_adapter_log_routing(self):
        """Test that adapter logs go to correct directory"""
        log_event(
            stage="ingestion",
            block="yfinance_adapter",
            level="INFO",
            msg="Test adapter log",
            extra={"adapter_id": "price_001"},
        )

        # ✅ Use mode-aware adapter log path
        manager = get_mode_manager()
        adapter_log = manager.get_log_dir() / "adapters"
        assert (
            adapter_log.exists()
        ), f"Adapter log directory should exist at {adapter_log}"

    def test_stage_log_routing(self):
        """Test that stage logs go to correct directory"""
        log_event(
            stage="data_collection",
            block="stage",
            level="INFO",
            msg="Test stage log",
            extra={"operation_id": "test456"},
        )

        # ✅ Use mode-aware stage log path
        manager = get_mode_manager()
        stage_log = manager.get_log_dir() / "stages"
        assert stage_log.exists(), f"Stage log directory should exist at {stage_log}"


class TestLogValidator:
    """Test JSONL log validation"""

    def test_validate_valid_log_entry(self):
        """Test validation of valid log entry"""
        valid_entry = {
            "timestamp": datetime.now().isoformat(),
            "stage": "test_stage",
            "block": "test_block",
            "level": "INFO",
            "message": "Test message",
        }

        result = LogValidator._validate_entry(valid_entry, 1)
        assert len(result["missing_fields"]) == 0
        assert result["invalid_level"] is False
        assert len(result.get("schema_errors", [])) == 0  # ✅ Check schema

    def test_validate_against_schema(self):
        """Test JSON schema validation"""
        valid_entry = {
            "timestamp": datetime.now().isoformat(),
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
            "timestamp": datetime.now().isoformat(),
            "stage": "test",
            "block": "test",
            "level": 123,  # ❌ Should be string
            "message": "Test",
        }

        errors = LogValidator.validate_against_schema(
            invalid_entry, LogValidator.LOG_ENTRY_SCHEMA
        )
        assert len(errors) > 0, "Should detect type error"

    def test_validate_missing_fields(self):
        """Test detection of missing required fields"""
        invalid_entry = {
            "timestamp": datetime.now().isoformat(),
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
            "timestamp": datetime.now().isoformat(),
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
            "timestamp": datetime.now().isoformat(),
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
            "timestamp": datetime.now().isoformat(),
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
        # ✅ Use mode-aware log directory
        manager = get_mode_manager()
        test_log = manager.get_log_dir() / "test_validation.jsonl"
        test_log.parent.mkdir(parents=True, exist_ok=True)

        with open(test_log, "w", encoding="utf-8") as f:
            # Valid entry
            valid_entry = {
                "timestamp": datetime.now().isoformat(),
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
        # ✅ Use mode-aware log directory
        manager = get_mode_manager()
        test_log = manager.get_log_dir() / "test_malformed.jsonl"
        test_log.parent.mkdir(parents=True, exist_ok=True)

        with open(test_log, "w", encoding="utf-8") as f:
            # Valid entry
            valid_entry = {
                "timestamp": datetime.now().isoformat(),
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

        stage = HealthCheckStage()

        # Check if BaseStage has been updated
        has_enhanced_logging = hasattr(stage, "operation_id")
        if not has_enhanced_logging:
            pytest.skip(
                "BaseStage not yet updated with enhanced logging. "
                "Please update src/marketpilot/data_farm/stages/base_stage.py "
                "with the enhanced version"
            )
            return

        # Execute stage with mock data
        data = {"adapters": [], "symbols": ["AAPL"]}
        result = await stage.execute(data)
        print(result)
        # Verify stage logged correctly (use mode-aware directory)
        manager = get_mode_manager()
        log_dir = manager.get_log_dir() / "stages"
        log_files = list(log_dir.rglob("*.jsonl"))
        assert len(log_files) > 0, f"Stage logs should exist in {log_dir}"

        # Find completion log with enhanced fields
        completion_log_found = False
        with open(log_files[0], "r", encoding="utf-8") as f:
            lines = f.readlines()

        for line in reversed(lines[-10:]):
            try:
                entry = json.loads(line)
                if entry.get("stage") == "health_check" and "Completed" in entry.get(
                    "message", ""
                ):
                    # ✅ FIX: Check in root of entry, not in extra dict
                    # The logger merges extra fields into root
                    required_fields = ["operation_id", "duration_ms", "success_flag"]

                    # Check if all required fields exist in the root of the entry
                    if all(field in entry for field in required_fields):
                        completion_log_found = True

                        # Additional validation
                        assert isinstance(
                            entry["operation_id"], str
                        ), "operation_id should be a string"
                        assert isinstance(
                            entry["duration_ms"], (int, float)
                        ), "duration_ms should be numeric"
                        assert isinstance(
                            entry["success_flag"], bool
                        ), "success_flag should be boolean"
                        assert (
                            entry["success_flag"] is True
                        ), "success_flag should be True for successful completion"

                        break
            except json.JSONDecodeError:
                continue

        if not completion_log_found:
            # Provide helpful debug info
            print("\n🔍 DEBUG: Recent log entries:")
            for line in lines[-5:]:
                try:
                    entry = json.loads(line)
                    print(
                        f"  Stage: {entry.get('stage')}, "
                        f"Message: {entry.get('message')}, "
                        f"Keys: {list(entry.keys())}"
                    )
                except Exception as e:
                    print(f"Error parsing line: {e}")

            pytest.fail(
                "Enhanced logging fields not found in completion log. "
                "Fields should be in root of entry (not in 'extra' dict)"
            )

        assert completion_log_found, "Should find completion log with enhanced fields"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
