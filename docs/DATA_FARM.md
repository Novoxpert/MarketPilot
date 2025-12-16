# Data Farm - Financial Data Pipeline

> Production-grade pipeline for collecting, cleaning, and exporting financial market data

---

## Overview

**Data Farm** ingests price (OHLCV) and news data from APIs, processes it through 7 stages, and exports clean Parquet files organized by symbol.

**Key Features**:
-    Automatic retry with exponential backoff
-    Cursor/offset pagination for large datasets
-    Timestamp normalization to Unix milliseconds
-    Deduplication and quality validation
-    Centralized JSONL logging

---

## Architecture

### Pipeline Flow

```
Health Check → Data Collection → NaN Cleaning 
  → Temporal Alignment → Deduplication 
  → Quality Check → Export (Parquet)
```

### Components

| Component | Purpose |
|-----------|---------|
| **ResilientDataFarm** | Orchestrator (initializes adapters, runs stages) |
| **Adapters** | Fetch data from APIs (price, news, fundamental) |
| **Stages** | Process data sequentially (7 stages) |
| **APIRetryHandler** | Retry logic with validation |
| **Logger** | JSONL logs per component |

### Adapters

| Adapter | Type | Pagination | Output |
|---------|------|------------|--------|
| **ResilientPriceAdapter** | OHLCV | Offset-based | `{symbol, timestamp, OHLCV}` |
| **ResilientNewsAdapter** | Articles | Cursor-based | `{news_id, symbol, title, assets}` |
| **ResilientFundamentalAdapter** | Financials | *(Coming soon)* | - |


### Pipeline Stages

| Stage | Purpose | Key Operations |
|-------|---------|----------------|
| **Health Check** | Verify API availability | HTTP GET `/health` endpoints |
| **Data Collection** | Fetch from adapters | Parallel ingestion with retry |
| **NaN Processing** | Clean missing values | Replace NaN/empty with defaults |
| **Temporal Alignment** | Normalize timestamps | Convert to Unix ms (int) |
| **Deduplication** | Remove duplicates | Symbol + timestamp keys |
| **Quality Assurance** | Validate data | Check pass rate threshold |
| **Data Export** | Save to Parquet | Asset-first structure |
---

## Output Structure

```
data/
├── BINANCE_BTCUSDT_P/
│   ├── price.parquet         # OHLCV data
│   ├── news.parquet          # News articles
│   └── symbol_info.json      # Metadata
├── BINANCE_ETHUSDT_P/
│   └── ...
└── __meta__/
    ├── manifest.jsonl        # Export manifest
    └── pipeline_stats.json   # Pipeline metrics

logs/
├── pipeline/current.jsonl
├── stages/
│   ├── health_check.jsonl
│   ├── data_collection.jsonl
│   └── ...
├── adapter/
│   ├── price_internal_001.jsonl
│   └── news_internal_001.jsonl
└── errors/current.jsonl
```

---

## Quick Start

### 1. Installation
 please read SETUP.md file

### 2. Configuration

**Environment variables** (`.env`):
```bash
cp .env.example .env
```

**Config file** (`configs/data/data_farm_config.yml`):
```yaml
target_symbols:
  - "BINANCE:BTCUSDT.P"
  - "BINANCE:ETHUSDT.P"

adapters:
  - id: price_internal_001
    type: price
    limit: 1000
    max_pages: 5000
    enable_pagination: true
    page_delay: 0.3
    
  - id: news_internal_001
    type: news
    limit: 100
    max_pages: 200
    page_delay: 0.5

quality:
  quality_threshold: 0.80  # 80% pass rate minimum
```

### 3. Run Pipeline

**Option A: CLI** (Interactive)
```bash
marketpilot-cli
Λ run-pipeline
```

**Option B: Python**
```python
from marketpilot.data_farm import ResilientDataFarm
from datetime import datetime, timedelta

farm = ResilientDataFarm()

result = await farm.run_complete_pipeline(
    symbols=["BINANCE:BTCUSDT.P"],
    start_date=datetime.utcnow() - timedelta(hours=24),
    end_date=datetime.utcnow()
)

print(f"   Exported {result['export_stats']['records_exported']} records")
```

---

## 🔧 Configuration Reference

### Adapter Fields

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `id` | string | required | Unique identifier |
| `type` | string | required | `price`, `news`, `fundamental` |
| `limit` | int | 1000 | Records per page |
| `enable_pagination` | bool | true | Enable/disable pagination |
| `max_pages` | int | 5000 | Max pages to fetch |
| `max_total_records` | int | 5M | Max total records |
| `page_delay` | float | 0.3 | Delay between pages (seconds) |
| `max_retries` | int | 3 | Retry attempts |
| `retry_delay` | float | 2.0 | Initial retry delay |
| `backoff_factor` | float | 2.0 | Exponential backoff multiplier |
| `timeout` | int | 30 | Request timeout (seconds) |

---

## Usage Examples

### 1. Basic Usage

```python
from marketpilot.data_farm import ResilientDataFarm
from datetime import datetime, timedelta

farm = ResilientDataFarm()

result = await farm.run_complete_pipeline(
    symbols=["BINANCE:BTCUSDT.P"],
    start_date=datetime.utcnow() - timedelta(hours=24),
    end_date=datetime.utcnow()
)
```

### 2. Historical Data (1 Month)

```python
result = await farm.run_complete_pipeline(
    symbols=["BINANCE:BTCUSDT.P", "BINANCE:ETHUSDT.P"],
    start_date=datetime(2025, 11, 1),
    end_date=datetime(2025, 12, 1)
)
```

### 3. Smoke Test

```python
result = await farm.run_smoke_test(["BINANCE:BTCUSDT.P"])

if result["success"]:
    print("   All adapters working")
else:
    for detail in result["details"]:
        print(f"{detail['adapter_id']}: {detail['status']}")
```

### 4. Read Exported Data

```python
import pandas as pd

df = pd.read_parquet("data/BINANCE_BTCUSDT_P/price.parquet")
print(f"Records: {len(df)}")
print(f"Avg price: ${df['close'].mean():.2f}")
```

### 5. Check Logs

```python
import json

with open("logs/adapter/price_internal_001.jsonl") as f:
    for line in f:
        log = json.loads(line)
        if log["level"] == "ERROR":
            print(f"Error: {log['message']}")
```

### Adapters Implementation

**Price Adapter (Offset Pagination)**:
```
URL: /price?symbol=X&start=...&limit=1000&offset=0

while has_more:
    fetch(offset=current_offset)
    current_offset += records_fetched
```

**News Adapter (Cursor Pagination)**:
```
URL: /news?asset_slug=X&limit=100&cursor=ABC123

while has_next:
    fetch(cursor=current_cursor)
    current_cursor = response["pagination"]["next_cursor"]
```

### Resilience Features

**Retry Logic**:
```python
retry_handler = create_retry_handler(
    adapter_id="price_internal_001",
    max_retries=3,
    retry_delay=2.0,
    backoff_factor=2.0
)

status, data = await retry_handler.fetch_with_retry(url, symbol)
```

**Concurrency Control**: Per-symbol locks prevent duplicate fetches

### Data Schemas

**Price**:
```json
{
  "symbol": "BINANCE:BTCUSDT.P",
  "timestamp": 1733049780000,
  "open": 95000.5,
  "high": 95500.0,
  "low": 94800.0,
  "close": 95200.0,
  "volume": 1234.56
}
```

**News**:
```json
{
  "news_id": "article-123",
  "symbol": "BINANCE:BTCUSDT.P",
  "timestamp": 1733049780000,
  "title": "Breaking News",
  "source": "Reuters",
  "assets_json": "[{...}]",
  "mapping_confidence": 1.0
}
```

### Logging

**Log Routing**:
- Errors → `logs/errors/current.jsonl`
- Adapters → `logs/adapter/{adapter_id}.jsonl`
- Stages → `logs/stages/{stage_name}.jsonl`
- Pipeline → `logs/pipeline/current.jsonl`

**Log Format**:
```json
{
  "timestamp": "2025-12-01T10:46:39Z",
  "stage": "data_collection",
  "block": "price_internal_001_adapter",
  "level": "INFO",
  "message": "Fetched 100 records",
  "symbol": "BINANCE:BTCUSDT.P",
  "duration_ms": 1234.56
}
```


**Check API Health**:
```bash
curl $PRICE_API_HEALTH_URL
# Should return: {"success": true, "version": "1.0.0"}
```

**View Error Logs**:
```bash
cat logs/errors/current.jsonl | jq
```

## Testing
please read TEST.md
