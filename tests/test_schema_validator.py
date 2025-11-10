"""
Unit Tests for Schema Validator
"""

import pytest
from marketpilot.utils.schema_validator import (
    SchemaValidator,
    validate_pipeline_stages,
)


class TestSchemaValidator:
    """Test schema validation functionality"""

    def test_valid_record_structure(self):
        """Test validation of valid record"""
        record = {
            "symbol": "AAPL",
            "adapter_id": "price_001",
            "vendor": "yfinance",
            "data": {
                "timestamp": "2025-01-01",
                "open": 150.0,
                "high": 155.0,
                "low": 148.0,
                "close": 152.0,
                "volume": 1000000,
            },
        }

        validator = SchemaValidator()
        # Test without schema
        missing = validator.validate_record_structure(record)
        assert (
            len(missing) == 0
        ), "Valid record should have no missing record-level fields"

        # Test with price schema validation
        missing_with_schema = validator.validate_record_structure(record, "price")
        assert (
            len(missing_with_schema) == 0
        ), "Valid price record should pass schema validation"

    def test_missing_symbol(self):
        """Test detection of missing symbol"""
        record = {
            "adapter_id": "price_001",
            "vendor": "yfinance",
            "data": {"timestamp": "2025-01-01"},
        }

        validator = SchemaValidator()
        missing = validator.validate_record_structure(record)

        assert "symbol" in missing, "Missing symbol should be detected"

    def test_missing_data_payload(self):
        """Test detection of missing data payload"""
        record = {"symbol": "AAPL", "adapter_id": "price_001", "vendor": "yfinance"}

        validator = SchemaValidator()
        missing = validator.validate_record_structure(record)

        assert "data" in missing, "Missing data payload should be detected"

    def test_validate_stage_output_success(self):
        """Test successful stage output validation"""
        data = {
            "raw_data": [
                {
                    "symbol": "AAPL",
                    "adapter_id": "price_001",
                    "vendor": "yfinance",
                    "data": {},
                }
            ]
        }

        validator = SchemaValidator()
        result = validator.validate_stage_output("data_collection", data, "raw_data")

        assert result is True, "Valid stage output should pass"

    def test_validate_stage_output_missing_key(self):
        """Test detection of missing expected key"""
        data = {"wrong_key": []}

        validator = SchemaValidator()
        result = validator.validate_stage_output("data_collection", data, "raw_data")

        assert result is False, "Missing key should fail validation"

    def test_validate_stage_output_wrong_type(self):
        """Test detection of wrong data type"""
        data = {"raw_data": "not a list"}

        validator = SchemaValidator()
        result = validator.validate_stage_output("data_collection", data, "raw_data")

        assert result is False, "Wrong type should fail validation"

    def test_field_coverage_calculation(self):
        """Test field coverage calculation"""
        records = [
            {"data": {"timestamp": "2025-01-01", "open": 150.0, "close": 152.0}},
            {"data": {"timestamp": "2025-01-02", "open": 151.0}},  # missing close
            {"data": {"timestamp": "2025-01-03", "open": 153.0, "close": 154.0}},
        ]

        validator = SchemaValidator()
        coverage = validator.get_field_coverage(records)

        assert coverage["timestamp"] == 100.0, "timestamp present in all records"
        assert coverage["open"] == 100.0, "open present in all records"
        assert coverage["close"] == pytest.approx(
            66.67, rel=0.1
        ), "close present in 2/3 records"

    def test_inter_stage_transfer_validation(self):
        """Test validation between consecutive stages"""
        prev_data = {
            "raw_data": [
                {"symbol": "AAPL", "adapter_id": "001", "vendor": "yf", "data": {}}
            ]
        }
        curr_data = {
            "processed_data": [
                {"symbol": "AAPL", "adapter_id": "001", "vendor": "yf", "data": {}}
            ]
        }

        validator = SchemaValidator()
        result = validator.validate_inter_stage_transfer(
            "data_collection",
            "nan_processing",
            prev_data,
            curr_data,
            "raw_data",
            "processed_data",
        )

        assert result is True, "Valid transfer should pass"


class TestPipelineValidation:
    """Test complete pipeline validation"""

    def test_complete_pipeline_validation(self):
        """Test validation of complete pipeline"""
        pipeline_data = {
            "raw_data": [
                {
                    "symbol": "AAPL",
                    "adapter_id": "price_001",
                    "vendor": "yfinance",
                    "data": {"timestamp": "2025-01-01", "open": 150.0},
                }
            ],
            "processed_data": [
                {
                    "symbol": "AAPL",
                    "adapter_id": "price_001",
                    "vendor": "yfinance",
                    "data": {"timestamp": "2025-01-01", "open": 150.0},
                }
            ],
            "aligned_data": [
                {
                    "symbol": "AAPL",
                    "adapter_id": "price_001",
                    "vendor": "yfinance",
                    "data": {"timestamp": "2025-01-01T00:00:00", "open": 150.0},
                }
            ],
            "unique_data": [
                {
                    "symbol": "AAPL",
                    "adapter_id": "price_001",
                    "vendor": "yfinance",
                    "data": {"timestamp": "2025-01-01T00:00:00", "open": 150.0},
                }
            ],
            "validated_data": [
                {
                    "symbol": "AAPL",
                    "adapter_id": "price_001",
                    "vendor": "yfinance",
                    "data": {"timestamp": "2025-01-01T00:00:00", "open": 150.0},
                }
            ],
        }

        report = validate_pipeline_stages(pipeline_data)

        assert report["validation_passed"] is True, "Valid pipeline should pass"
        assert len(report["stages_validated"]) > 0, "Should validate multiple stages"
        assert len(report["errors"]) == 0, "No errors should be present"

    def test_pipeline_validation_with_errors(self):
        """Test pipeline validation with missing data"""
        pipeline_data = {
            "raw_data": [{"symbol": "AAPL"}],  # Missing required fields
            "processed_data": [],
        }

        report = validate_pipeline_stages(pipeline_data)

        # Should still complete but may have warnings
        assert "stages_validated" in report
        assert isinstance(report["warnings"], list)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
