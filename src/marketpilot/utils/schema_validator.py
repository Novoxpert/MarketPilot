"""
Schema Validator - MP-008: Validate inter-stage data transfer
Simple validator to check schema consistency between pipeline stages
"""

from typing import Dict, Any, List, Set
from marketpilot.utils.logger import log_event
from marketpilot.config.config_loader import get_required_columns


class SchemaValidator:
    """Validate data schema consistency between stages"""

    # Record-level fields that must exist in all records
    RECORD_LEVEL_FIELDS = ["symbol", "adapter_id", "vendor", "data"]

    @staticmethod
    def get_required_fields(schema_type: str) -> List[str]:
        """
        Get required fields from schema file

        Args:
            schema_type: Type of schema (price, news, fundamental)

        Returns:
            List of required field names
        """
        try:
            return get_required_columns(schema_type)
        except Exception as e:
            log_event(
                stage="validation",
                block="schema_validator",
                level="WARNING",
                msg=f"Could not load schema for {schema_type}: {str(e)}",
            )
            return []

    @staticmethod
    def validate_stage_output(
        stage_name: str, data: Dict[str, Any], expected_key: str
    ) -> bool:
        """
        Validate that stage output contains expected data key

        Args:
            stage_name: Name of the stage
            data: Output data from stage
            expected_key: Expected key in data dict (e.g., 'raw_data', 'processed_data')

        Returns:
            True if valid, False otherwise
        """
        if expected_key not in data:
            log_event(
                stage="validation",
                block="schema_validator",
                level="ERROR",
                msg=f"Missing expected key '{expected_key}' in {stage_name} output",
                extra={"stage": stage_name, "expected_key": expected_key},
            )
            return False

        records = data.get(expected_key, [])
        if not isinstance(records, list):
            log_event(
                stage="validation",
                block="schema_validator",
                level="ERROR",
                msg=f"Expected list for '{expected_key}', got {type(records)}",
                extra={"stage": stage_name},
            )
            return False

        log_event(
            stage="validation",
            block="schema_validator",
            level="INFO",
            msg=f"Stage output validated: {len(records)} records",
            extra={"stage": stage_name, "record_count": len(records)},
        )
        return True

    @staticmethod
    def validate_record_structure(
        record: Dict[str, Any], schema_type: str = None
    ) -> List[str]:
        """
        Validate individual record structure

        Args:
            record: Single data record
            schema_type: Optional schema type to validate data payload

        Returns:
            List of missing critical fields
        """
        missing_fields = []

        # Check record-level fields
        for field in SchemaValidator.RECORD_LEVEL_FIELDS:
            if field not in record or record.get(field) is None:
                missing_fields.append(field)

        # If schema_type provided, validate data payload against schema
        if schema_type and "data" in record:
            required_fields = SchemaValidator.get_required_fields(schema_type)
            record_data = record.get("data", {})

            # Fields that exist at record level (not in data payload)
            record_level_fields = {"symbol", "adapter_id", "vendor"}

            for field in required_fields:
                # Skip fields that should be at record level
                if field in record_level_fields:
                    continue

                if field not in record_data:
                    missing_fields.append(f"data.{field}")

        return missing_fields

    @staticmethod
    def validate_inter_stage_transfer(
        prev_stage: str,
        curr_stage: str,
        prev_data: Dict[str, Any],
        curr_data: Dict[str, Any],
        prev_key: str,
        curr_key: str,
    ) -> bool:
        """
        Validate data consistency between two consecutive stages

        Args:
            prev_stage: Previous stage name
            curr_stage: Current stage name
            prev_data: Data from previous stage
            curr_data: Data from current stage
            prev_key: Data key in previous stage
            curr_key: Data key in current stage

        Returns:
            True if transfer is valid
        """
        prev_records = prev_data.get(prev_key, [])
        curr_records = curr_data.get(curr_key, [])

        # Check record count
        if len(curr_records) > len(prev_records):
            log_event(
                stage="validation",
                block="schema_validator",
                level="WARNING",
                msg="Record count increased between stages (unexpected)",
                extra={
                    "from_stage": prev_stage,
                    "to_stage": curr_stage,
                    "prev_count": len(prev_records),
                    "curr_count": len(curr_records),
                },
            )

        # Check if records have consistent structure
        if curr_records:
            sample_record = curr_records[0]

            # Try to detect schema type from adapter_id
            adapter_id = sample_record.get("adapter_id", "")
            schema_type = None
            if "price" in adapter_id.lower():
                schema_type = "price"
            elif "news" in adapter_id.lower():
                schema_type = "news"
            elif "fundamental" in adapter_id.lower():
                schema_type = "fundamental"

            missing = SchemaValidator.validate_record_structure(
                sample_record, schema_type
            )

            if missing:
                log_event(
                    stage="validation",
                    block="schema_validator",
                    level="WARNING",
                    msg="Missing critical fields in records",
                    extra={
                        "stage": curr_stage,
                        "missing_fields": missing,
                        "schema_type": schema_type,
                    },
                )
                return False

        log_event(
            stage="validation",
            block="schema_validator",
            level="INFO",
            msg="Inter-stage transfer validated",
            extra={
                "from_stage": prev_stage,
                "to_stage": curr_stage,
                "records_transferred": len(curr_records),
            },
        )
        return True

    @staticmethod
    def get_field_coverage(records: List[Dict[str, Any]]) -> Dict[str, float]:
        """
        Calculate field coverage across all records

        Args:
            records: List of data records

        Returns:
            Dict with field names and coverage percentage
        """
        if not records:
            return {}

        # Collect all unique fields
        all_fields: Set[str] = set()
        for record in records:
            record_data = record.get("data", {})
            if isinstance(record_data, dict):
                all_fields.update(record_data.keys())

        # Calculate coverage for each field
        coverage = {}
        total_records = len(records)

        for field in all_fields:
            present_count = sum(
                1
                for r in records
                if field in r.get("data", {})
                and r.get("data", {}).get(field) is not None
            )
            coverage[field] = (present_count / total_records) * 100

        return coverage


def validate_pipeline_stages(pipeline_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate schema consistency across all pipeline stages

    Args:
        pipeline_data: Complete pipeline data

    Returns:
        Validation report
    """
    validator = SchemaValidator()
    report = {
        "validation_passed": True,
        "stages_validated": [],
        "warnings": [],
        "errors": [],
    }

    # Stage data key mapping
    stage_keys = {
        "health_check": None,  # No data records
        "data_collection": "raw_data",
        "nan_processing": "processed_data",
        "temporal_alignment": "aligned_data",
        "deduplication": "unique_data",
        "quality_assurance": "validated_data",
        "data_export": "validated_data",
    }

    prev_key = None
    prev_stage = None

    for stage, data_key in stage_keys.items():
        if data_key is None:
            continue

        # Validate stage output
        if not validator.validate_stage_output(stage, pipeline_data, data_key):
            report["errors"].append(f"Stage {stage} failed validation")
            report["validation_passed"] = False
            continue

        # Validate inter-stage transfer
        if prev_key and prev_stage:
            validator.validate_inter_stage_transfer(
                prev_stage, stage, pipeline_data, pipeline_data, prev_key, data_key
            )

        # Calculate field coverage
        records = pipeline_data.get(data_key, [])
        coverage = validator.get_field_coverage(records)

        # Check for low coverage fields (< 50%)
        for field, cov in coverage.items():
            if cov < 50:
                report["warnings"].append(
                    f"Low coverage in {stage}: {field} ({cov:.1f}%)"
                )

        report["stages_validated"].append(
            {"stage": stage, "record_count": len(records), "field_coverage": coverage}
        )

        prev_key = data_key
        prev_stage = stage

    log_event(
        stage="validation",
        block="pipeline_validator",
        level="INFO" if report["validation_passed"] else "ERROR",
        msg="Pipeline validation complete",
        extra={
            "stages_validated": len(report["stages_validated"]),
            "warnings": len(report["warnings"]),
            "errors": len(report["errors"]),
        },
    )

    return report


# Example usage
if __name__ == "__main__":
    # Test validator with schema loading
    test_record = {
        "symbol": "AAPL",
        "adapter_id": "price_001",
        "vendor": "yfinance",
        "data": {"timestamp": "2025-01-01", "open": 150.0, "close": 152.0},
    }

    validator = SchemaValidator()

    # Test without schema validation
    missing = validator.validate_record_structure(test_record)
    print(f"Missing fields (no schema): {missing}")

    # Test with price schema validation
    missing_with_schema = validator.validate_record_structure(test_record, "price")
    print(f"Missing fields (with price schema): {missing_with_schema}")

    # Show required fields from schema
    price_fields = validator.get_required_fields("price")
    print(f"Required price fields from schema: {price_fields}")
