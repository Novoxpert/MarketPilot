# Schema Validation Documentation

## Overview
This document defines expected schemas and validation rules for inter-stage data transfer in the Market Pilot Data Farm pipeline.

---

## Stage Data Flow

```
HealthCheck → DataCollection → NaNProcessing → TemporalAlignment → Deduplication → QualityAssurance → DataExport
              (raw_data)      (processed_data)  (aligned_data)     (unique_data)   (validated_data)  (validated_data)
```

---

## Critical Fields

### Record-Level Fields (Must exist in all records)
- `symbol` (string): Asset symbol
- `adapter_id` (string): Unique adapter identifier
- `vendor` (string): Data vendor name
- `data` (dict): Actual data payload
- `ingested_at` (string): Timestamp of ingestion

### Price Data Fields (in `data` payload)
- `timestamp` (datetime): Data timestamp
- `open` (float): Opening price
- `high` (float): Highest price
- `low` (float): Lowest price
- `close` (float): Closing price
- `volume` (integer): Trading volume

### News Data Fields (in `data` payload)
- `symbol` (string): Asset symbol
- `startdate` (datetime): Start date of news range
- `enddate` (datetime): End date of news range
- `data` (list): List of news items

### Fundamental Data Fields (in `data` payload)
- `symbol` (string): Asset symbol
- `startdate` (datetime): Start date of fundamental data
- `enddate` (datetime): End date of fundamental data
- `data` (dict): Fundamental data object

---

## Validation Rules

### 1. Stage Output Validation
Each stage must output data in expected key:
- `data_collection` → `raw_data`
- `nan_processing` → `processed_data`
- `temporal_alignment` → `aligned_data`
- `deduplication` → `unique_data`
- `quality_assurance` → `validated_data`

### 2. Record Structure Validation
Every record must contain:
- All record-level fields
- Non-null `symbol` and `adapter_id`
- Non-empty `data` payload

### 3. Inter-Stage Transfer Validation
Between consecutive stages:
- Record count should not increase (can decrease due to filtering)
- Critical fields must remain present
- Field coverage should not drop below 50%

### 4. Schema Deviation Warnings
System logs warnings when:
- Missing required fields
- Field coverage < 50%
- Unexpected field additions/removals
- Data type mismatches

---

## Usage

### In Pipeline Code
```python
from marketpilot.utils.schema_validator import validate_pipeline_stages

# After pipeline execution
validation_report = validate_pipeline_stages(pipeline_data)

if not validation_report["validation_passed"]:
    print("Validation errors:", validation_report["errors"])
```

### Manual Validation
```python
from marketpilot.utils.schema_validator import SchemaValidator

validator = SchemaValidator()

# Validate single record
missing_fields = validator.validate_record_structure(record)

# Validate stage output
is_valid = validator.validate_stage_output("data_collection", data, "raw_data")

# Check field coverage
coverage = validator.get_field_coverage(records)
```

---

## Expected Behavior

### ✅ Valid Pipeline
- All stages complete successfully
- No missing critical fields
- Field coverage ≥ 50% for all fields
- Consistent record structure across stages

### ⚠️ Warning Conditions
- Field coverage between 30-50%
- Non-critical field missing
- Minor timestamp format issues

### ❌ Error Conditions
- Missing critical fields (symbol, adapter_id, data)
- Stage output missing expected key
- Empty data payloads
- Invalid data types for numeric fields

---

## Testing

Run schema validation tests:
```bash
pytest tests/test_schema_validator.py -v
poetry run pytest tests/test_schema_validator.py -v
```

Manual pipeline validation:
```bash
python scripts/validate_pipeline.py --config config/data_farm_config.yaml

```

---

## Notes

- Validation runs automatically after each stage execution
- Logs written to `/logs/stages/validation_*.jsonl`
- Validation does not stop pipeline execution (logs warnings only)
- Use `validation_report` for post-execution analysis

---
