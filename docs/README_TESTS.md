poetry run python scripts/run_data_farm.py
poetry run pytest tests/test_simple_stages.py -v
# Market Pilot Unit Tests

## Overview
Comprehensive unit test suite for Market Pilot Data Farm covering adapters, stages, and complete pipeline integration.

## Test Coverage Goal
**Target: ≥80% code coverage**

## Test Structure

```
tests/
├── conftest.py              # Pytest configuration & fixtures
├── test_adapters.py         # Adapter unit tests
├── test_stages.py          # Stage unit tests
├── test_integration.py     # Integration tests
└── README_TESTS.md         # This file
```

## Running Tests
### Run all tests with coverage
```bash
pytest tests/ \
    --cov=marketpilot \
    --cov-report=term-missing \
    --cov-report=html:htmlcov \
    --cov-fail-under=80 \
    -v \
    --tb=short
```
### Manual Execution
```bash
# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=marketpilot --cov-report=html

# Run specific test file
pytest tests/test_adapters.py -v

# Run specific test
pytest tests/test_adapters.py::TestResilientPriceAdapter::test_price_adapter_ingest_success -v
```

### Test Categories
```bash
# Run only unit tests
pytest tests/ -m unit

# Run only integration tests
pytest tests/ -m integration

# Run smoke tests
pytest tests/ -m smoke
```

## Test Files Description

### `test_adapters.py`
Tests for data adapters:
- ✅ Adapter initialization
- ✅ Successful data ingestion
- ✅ Schema validation
- ✅ Numeric value validation
- ✅ Error handling

**Classes:**
- `TestResilientPriceAdapter`
- `TestResilientNewsAdapter`
- `TestResilientFundamentalAdapter`

### `test_stages.py`
Tests for pipeline stages:
- ✅ Health Check Stage
- ✅ Data Collection Stage
- ✅ NaN Processing Stage
- ✅ Temporal Alignment Stage
- ✅ Deduplication Stage
- ✅ Quality Assurance Stage
- ✅ Data Export Stage

**Classes:**
- `TestHealthCheckStage`
- `TestNaNProcessingStage`
- `TestTemporalAlignmentStage`
- `TestDeduplicationStage`
- `TestQualityAssuranceStage`
- `TestDataExportStage`

### `test_integration.py`
End-to-end integration tests:
- ✅ Complete pipeline execution
- ✅ Multi-symbol processing
- ✅ QA statistics validation
- ✅ Export functionality
- ✅ Error handling
- ✅ Logging integration

**Classes:**
- `TestPipelineIntegration`
- `TestDataFarmConfiguration`
- `TestErrorHandling`
- `TestLoggingIntegration`

## Test Mode Features

All tests automatically run in **test mode** via `conftest.py`:
- 🔧 Logs written to `logs_test/` directory
- 🔧 Test data isolated from production
- 🔧 Automatic cleanup after tests

## Key Test Scenarios

### Adapter Tests
```python
# Test successful ingestion
result = await adapter.execute_ingest("AAPL")
assert result["success"] is True

# Test schema validation
data = result["data"]
assert "timestamp" in data
assert "open" in data
```

### Stage Tests
```python
# Test NaN processing
data_with_nans = {"raw_data": [...]}
result = await nan_stage.execute(data_with_nans)
assert result["nan_stats"]["nan_count"] == 2

# Test deduplication
data_with_dupes = {"aligned_data": [...]}
result = await dedup_stage.execute(data_with_dupes)
assert result["dedup_stats"]["duplicates_removed"] == 1
```

### Integration Tests
```python
# Test complete pipeline
farm = ResilientDataFarm()
result = await farm.run_complete_pipeline(["AAPL", "GOOGL"])
assert "validated_data" in result
assert result["validation_report"]["validation_passed"]
```

## Coverage Report

After running tests, view coverage in browser:
```bash
# Mac
open htmlcov/index.html

# Linux
xdg-open htmlcov/index.html

# Windows
start htmlcov/index.html
```

## Fixtures Available

Common fixtures defined in `conftest.py`:
- `sample_adapters` - Mock adapter data
- `sample_symbols` - Test symbols (AAPL, GOOGL, MSFT)
- `sample_price_data` - Mock price records

## Mocking External APIs

Tests use mock data instead of real API calls:
```python
# Adapters return mock data
mock_data = {
    "symbol": "AAPL",
    "timestamp": "2024-01-01T00:00:00",
    "open": 150.0,
    "close": 152.0
}
```

## Troubleshooting

### Import Errors
```bash
# Ensure correct PYTHONPATH
export PYTHONPATH="${PYTHONPATH}:src"

# Or use pytest.ini configuration
```

### Async Test Errors
```bash
# Install pytest-asyncio
pip install pytest-asyncio

# Ensure asyncio_mode = auto in pytest.ini
```

### Coverage Too Low
```bash
# View detailed coverage
pytest --cov=marketpilot --cov-report=term-missing

# Check which files need more tests
```

## CI Integration

Tests run automatically in CI pipeline (see `.github/workflows/ci.yml`):
- ✅ Linting with flake8
- ✅ Formatting check with black
- ✅ Unit tests with pytest
- ✅ Coverage report generation

## Best Practices

1. **Test Naming**: Use descriptive names
   ```python
   def test_adapter_handles_missing_data_gracefully()
   ```

2. **Arrange-Act-Assert**: Follow AAA pattern
   ```python
   # Arrange
   adapter = ResilientPriceAdapter(config)

   # Act
   result = await adapter.execute_ingest("AAPL")

   # Assert
   assert result["success"] is True
   ```

3. **Use Fixtures**: Reuse common test data
   ```python
   @pytest.fixture
   def sample_config():
       return {"vendor": "yfinance", ...}
   ```
# in run_data_farm_complete.py - lines 207-208

# Test 1: Last 1 hour
START_DATE = END_DATE - timedelta(hours=1)

# Test 2: Last 7 days
START_DATE = END_DATE - timedelta(days=7)

# Test 3: Specific range
START_DATE = datetime(2025, 1, 1, 0, 0, 0)
END_DATE = datetime(2025, 1, 7, 23, 59, 59)


?asset_slug=bitcoin&from_date=2025-12-01T07%3A08%3A00Z&to_date=2025-12-01T07%3A09%3A00Z&limit=100&sort_by=releasedAt&order=desc
pagination