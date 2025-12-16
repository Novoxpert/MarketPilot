# Comprehensive Test Guide - With Mode Manager

## Key Features

   **Test Mode Isolation**: Logs in `logs_test/` and data in `data_test/`  
   **Mode Manager Integration**: Full integration with mode system  
   **Comprehensive Coverage**: Complete coverage of adapters, stages, and integration  

---

## Test Structure

```
tests/
├── conftest.py              # Shared configuration (with Mode Manager)
├── test_adapters.py         # Adapter tests
├── test_stages.py           # Pipeline stage tests
└── test_integration.py      # Integration tests
```

### Folder Structure During Tests

```
project/
├── logs_test/               # Test logs (isolated)
│   ├── pipeline/
│   ├── stages/
│   ├── adapters/
│   └── errors/
├── data_test/               # Test data (isolated)
│   ├── BINANCE_BTCUSDT_P/
│   └── __meta__/
└── logs/                    # Normal logs (untouched)
    └── /                # Normal data (untouched)
```

---


## Running Tests

### Run All Tests
```bash
pytest
```

**Result:**
-    Test mode activated
-    Logs saved to `logs_test/`
-    Data saved to `data_test/`

### Run Specific File
```bash
pytest tests/test_adapters.py
```

### Run Specific Test
```bash
pytest tests/test_adapters.py::test_price_adapter_initialization
```

### Run with Coverage
```bash
pytest --cov=marketpilot --cov-report=html
```

---

## Using Markers

### Filter by Type
```bash
# Only unit tests
pytest -m unit

# Only integration tests
pytest -m integration

# Only adapter tests
pytest -m adapter

# Only stage tests
pytest -m stage

# Only pipeline tests
pytest -m pipeline

# Only smoke tests
pytest -m smoke
```

---


## Inspecting Test Logs

### During Test Execution

```bash
# Run tests without cleanup (for debugging)
pytest --no-cov -v

# Check logs (before test completion)
cat logs_test/pipeline/current.jsonl
cat logs_test/adapters/test_price_adapter.jsonl
cat logs_test/stages/data_collection.jsonl
cat logs_test/errors/current.jsonl
```

### Log Structure

```json
{
  "timestamp": "2025-12-07T10:30:00.000Z",
  "stage": "data_collection",
  "block": "test_price_adapter",
  "level": "INFO",
  "message": "Fetched 100 records",
  "test_mode": true,
  "symbol": "BINANCE:BTCUSDT.P"
}
```

---

##    Test Checklist

### Unit Tests (Fast)
-    `test_price_adapter_initialization`
-    `test_price_adapter_transform_response`
-    `test_news_adapter_initialization`
-    `test_news_adapter_transform_response`
-    `test_fundamental_adapter_initialization`
-    `test_nan_processing_basic`
-    `test_temporal_alignment_iso_string`
-    `test_deduplication_removes_duplicates`
-    `test_qa_pass`

### Integration Tests (Slower)
-    `test_data_farm_initialization`
-    `test_smoke_test_basic`
-    `test_complete_pipeline_with_mock`
-    `test_pipeline_handles_adapter_failure`
-    `test_logs_created_in_test_directory`

---


## Best Practices

### 1. Always Use Test Mode
```python
@pytest.fixture(scope="session", autouse=True)
def setup_test_mode():
    set_test_mode()
    yield
```

### 2. Verify Test Isolation
```python
def test_isolation():
    """Tests should not affect logs/ and data/"""
    manager = get_mode_manager()
    assert manager.is_test_mode
    assert not Path("logs/test_artifacts").exists()
```

### 3. Use Fixtures for Mocks
```python
@pytest.fixture
def mock_adapter(mock_env_vars):
    with patch.dict('os.environ', mock_env_vars):
        yield create_adapter()
```

---

## Quick Commands Summary

```bash
# Quick run
pytest -v

# With coverage
pytest --cov=marketpilot --cov-report=html

# Only unit tests
pytest -m unit

# Only integration tests
pytest -m integration

```

---


## Support

For issues or questions:
1. Check logs_test/errors/current.jsonl
2. Run with `pytest -vv --tb=long`
3. Check conftest.py
4. Check Mode Manager status

