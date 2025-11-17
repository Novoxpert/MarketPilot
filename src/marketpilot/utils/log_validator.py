"""
JSONL Log Validator
Validates that log files are properly formatted and contain required fields
Includes JSON schema validation
Includes JSON schema validation
"""

import json
from pathlib import Path
from typing import Dict, Any, List
from datetime import datetime


class LogValidator:
    """Validate JSONL log files"""

    # Required fields for all log entries
    REQUIRED_FIELDS = ["timestamp", "stage", "block", "level", "message"]

    # Required fields for stage/adapter logs
    STAGE_REQUIRED_FIELDS = REQUIRED_FIELDS + [
        "operation_id",
        "duration_ms",
        "success_flag",
    ]

    # Valid log levels
    VALID_LEVELS = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]

    #  JSON Schema for log entries
    LOG_ENTRY_SCHEMA = {
        "type": "object",
        "required": ["timestamp", "stage", "block", "level", "message"],
        "properties": {
            "timestamp": {
                "type": "string",
                "format": "date-time",
                "description": "ISO 8601 timestamp",
            },
            "stage": {"type": "string", "description": "Pipeline stage name"},
            "block": {"type": "string", "description": "Component block name"},
            "level": {
                "type": "string",
                "enum": ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
                "description": "Log level",
            },
            "message": {"type": "string", "description": "Log message"},
            "extra": {"type": "object", "description": "Additional fields"},
        },
    }

    #  Schema for error logs
    ERROR_LOG_SCHEMA = {
        "type": "object",
        "required": ["timestamp", "stage", "block", "level", "message"],
        "properties": {
            "timestamp": {"type": "string", "format": "date-time"},
            "stage": {"type": "string"},
            "block": {"type": "string"},
            "level": {"type": "string", "enum": ["ERROR", "CRITICAL"]},
            "message": {"type": "string"},
            "error_type": {"type": "string"},
            "error_message": {"type": "string"},
            "operation_id": {"type": "string"},
            "success_flag": {"type": "boolean", "enum": [False]},
        },
    }

    @staticmethod
    def validate_against_schema(
        entry: Dict[str, Any], schema: Dict[str, Any]
    ) -> List[str]:
        """
        Validate entry against JSON schema

        Args:
            entry: Log entry to validate
            schema: JSON schema

        Returns:
            List of validation errors
        """
        errors = []

        # Check required fields
        required = schema.get("required", [])
        for field in required:
            if field not in entry:
                errors.append(f"Missing required field: {field}")

        # Check field types and values
        properties = schema.get("properties", {})
        for field, rules in properties.items():
            if field in entry:
                value = entry[field]

                # Check type
                if "type" in rules:
                    expected_type = rules["type"]
                    if expected_type == "string" and not isinstance(value, str):
                        errors.append(
                            f"Field '{field}' should be string, got {type(value).__name__}"
                        )
                    elif expected_type == "object" and not isinstance(value, dict):
                        errors.append(
                            f"Field '{field}' should be object, got {type(value).__name__}"
                        )
                    elif expected_type == "boolean" and not isinstance(value, bool):
                        errors.append(
                            f"Field '{field}' should be boolean, got {type(value).__name__}"
                        )

                # Check enum
                if "enum" in rules:
                    if value not in rules["enum"]:
                        errors.append(
                            f"Field '{field}' value '{value}' not in allowed values: {rules['enum']}"
                        )

        return errors

    @staticmethod
    def validate_log_file(file_path: Path) -> Dict[str, Any]:
        """
        Validate a JSONL log file

        Args:
            file_path: Path to log file

        Returns:
            Validation report
        """
        report = {
            "file": str(file_path),
            "valid": True,
            "total_entries": 0,
            "malformed_entries": [],
            "missing_fields": [],
            "invalid_levels": [],
            "errors": [],
        }

        if not file_path.exists():
            report["valid"] = False
            report["errors"].append("File does not exist")
            return report

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                line_num = 0
                for line in f:
                    line_num += 1
                    line = line.strip()

                    if not line:  # Skip empty lines
                        continue

                    try:
                        # Try to parse JSON
                        entry = json.loads(line)
                        report["total_entries"] += 1

                        # Validate entry structure
                        validation_result = LogValidator._validate_entry(
                            entry, line_num
                        )

                        if validation_result["missing_fields"]:
                            report["missing_fields"].append(
                                {
                                    "line": line_num,
                                    "missing": validation_result["missing_fields"],
                                }
                            )
                            report["valid"] = False

                        if validation_result["invalid_level"]:
                            report["invalid_levels"].append(
                                {"line": line_num, "level": entry.get("level")}
                            )
                            report["valid"] = False

                    except json.JSONDecodeError as e:
                        report["malformed_entries"].append(
                            {"line": line_num, "error": str(e), "content": line[:100]}
                        )
                        report["valid"] = False

        except Exception as e:
            report["valid"] = False
            report["errors"].append(f"Failed to read file: {str(e)}")

        return report

    @staticmethod
    def _validate_entry(entry: Dict[str, Any], line_num: int) -> Dict[str, Any]:
        """
        Validate a single log entry

        Args:
            entry: Log entry dictionary
            line_num: Line number in file

        Returns:
            Validation result
        """
        result = {"missing_fields": [], "invalid_level": False}

        # Check required fields
        for field in LogValidator.REQUIRED_FIELDS:
            if field not in entry:
                result["missing_fields"].append(field)

        # Check log level
        if "level" in entry and entry["level"] not in LogValidator.VALID_LEVELS:
            result["invalid_level"] = True

        # Validate timestamp format
        if "timestamp" in entry:
            try:
                datetime.fromisoformat(entry["timestamp"].replace("Z", "+00:00"))
            except (ValueError, AttributeError):
                result["missing_fields"].append("timestamp (invalid format)")

        return result

    @staticmethod
    def validate_stage_logs(entry: Dict[str, Any]) -> List[str]:
        """
        Validate stage/adapter specific fields

        Args:
            entry: Log entry

        Returns:
            List of missing fields
        """
        missing = []

        # Check if this is a completion log (should have metrics)
        if "Completed" in entry.get("message", "") or "Failed" in entry.get(
            "message", ""
        ):
            for field in ["operation_id", "duration_ms", "success_flag"]:
                if field not in entry.get("extra", {}):
                    missing.append(field)

        return missing

    @staticmethod
    def validate_all_logs(log_dir: Path = Path("logs")) -> Dict[str, Any]:
        """
        Validate all log files in log directory

        Args:
            log_dir: Base log directory

        Returns:
            Complete validation report
        """
        report = {
            "timestamp": datetime.now().isoformat(),
            "log_directory": str(log_dir),
            "overall_valid": True,
            "files_validated": [],
            "summary": {
                "total_files": 0,
                "valid_files": 0,
                "invalid_files": 0,
                "total_entries": 0,
                "malformed_entries": 0,
            },
        }

        if not log_dir.exists():
            report["overall_valid"] = False
            report["error"] = "Log directory does not exist"
            return report

        # Find all JSONL files
        log_files = list(log_dir.rglob("*.jsonl"))
        report["summary"]["total_files"] = len(log_files)

        for log_file in log_files:
            file_report = LogValidator.validate_log_file(log_file)
            report["files_validated"].append(file_report)

            if file_report["valid"]:
                report["summary"]["valid_files"] += 1
            else:
                report["summary"]["invalid_files"] += 1
                report["overall_valid"] = False

            report["summary"]["total_entries"] += file_report["total_entries"]
            report["summary"]["malformed_entries"] += len(
                file_report["malformed_entries"]
            )

        return report

    @staticmethod
    def print_report(report: Dict[str, Any]):
        """Print validation report in readable format"""
        print("=" * 60)
        print("JSONL LOG VALIDATION REPORT")
        print("=" * 60)
        print()
        print(f"Log Directory: {report['log_directory']}")
        print(f"Timestamp: {report['timestamp']}")
        print()
        print("Summary:")
        print(f"  Total Files: {report['summary']['total_files']}")
        print(f"  Valid Files: {report['summary']['valid_files']}")
        print(f"  Invalid Files: {report['summary']['invalid_files']}")
        print(f"  Total Entries: {report['summary']['total_entries']}")
        print(f"  Malformed Entries: {report['summary']['malformed_entries']}")
        print()

        if report["overall_valid"]:
            print(" All log files are valid!")
        else:
            print(" Some log files have issues:")
            print()

            for file_report in report["files_validated"]:
                if not file_report["valid"]:
                    print(f"  File: {file_report['file']}")

                    if file_report["malformed_entries"]:
                        print(
                            f"    Malformed entries: {len(file_report['malformed_entries'])}"
                        )

                    if file_report["missing_fields"]:
                        print(
                            f"    Missing fields: {len(file_report['missing_fields'])}"
                        )

                    if file_report["invalid_levels"]:
                        print(
                            f"    Invalid levels: {len(file_report['invalid_levels'])}"
                        )

                    print()

        print("=" * 60)


# Example usage
if __name__ == "__main__":
    validator = LogValidator()

    # Validate all logs
    report = validator.validate_all_logs()
    validator.print_report(report)

    # Save report to file
    report_path = Path("logs/validation_report.json")
    report_path.parent.mkdir(parents=True, exist_ok=True)

    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    print(f"\nDetailed report saved to: {report_path}")
