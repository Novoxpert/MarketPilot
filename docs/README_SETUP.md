# MarketPilot - Developer Setup Guide

Quick guide to get your development environment up and running.

---

## Prerequisites

- **Python 3.11+** - [Download](https://www.python.org/downloads/)
- **Poetry** - [Install](https://python-poetry.org/docs/#installation)
- **Git**

Verify installations:
```bash
python --version    # 3.11+
poetry --version
git --version
```

---

## Quick Setup

```bash
# 1. Clone repository
git clone https://github.com/Novoxpert/MarketPilot.git
cd MarketPilot

# 2. Install dependencies
poetry install

# 3. Configure environment
cp .env.example .env
# Edit .env with your API keys

# 4. Install pre-commit hooks
# poetry run pre-commit install

# 5. Verify setup
poetry run pytest
```

---

## Get API Keys

Edit `.env` and replace placeholders with your actual keys.

---

## Common Commands

```bash
# Activate environment
poetry env activate

# Run tests
poetry run pytest

# Format code
poetry run black .

# Lint code
poetry run flake8 .

# Add dependency
poetry add package-name

# Add dev dependency
poetry add --group dev package-name
```

---

---

## Troubleshooting

**Dependency conflicts:**
```bash
rm poetry.lock
poetry install
```

**Wrong Python version:**
```bash
poetry env use python3.11
poetry install
```

**Pre-commit not working:**
```bash
poetry run pre-commit install
```

**Import errors:**
```bash
poetry shell  # Activate environment first
```

**API keys not loading:**
- Check `.env` exists in project root
- No spaces around `=` in `.env`
---

## Verify Installation

```bash
# Check all dependencies installed
poetry show

# Run all checks
poetry run pytest && poetry run black --check . && poetry run flake8 .
```

---
# Log Verification Guide

## View Log Files

### PowerShell
```powershell
Get-Content logs\adapters\adapters_*.jsonl
Get-Content logs\stages\stages_*.jsonl
Get-Content logs\errors\errors_*.jsonl
Get-Content logs\pipeline\pipeline_*.jsonl
```

### Linux/macOS
```bash
cat logs/adapters/adapters_*.jsonl
cat logs/stages/stages_*.jsonl
cat logs/errors/errors_*.jsonl
cat logs/pipeline/pipeline_*.jsonl
```

## Pretty Print (Optional)

With `jq`:
```bash
cat logs/adapters/adapters_*.jsonl | jq .
```

With Python:
```bash
poetry run python -c "import json; [print(json.dumps(json.loads(line), indent=2)) for line in open('logs/adapters/adapters_20250103.jsonl')]"
```

## Expected Output

Each log line should be valid JSON with these fields:
```json
{"timestamp": "2025-01-03T14:30:00", "stage": "ingestion", "block": "alphavantage_adapter", "level": "INFO", "message": "Fetched data", "symbol": "AAPL"}
```

## Verification Checklist

- [ ] All directories exist: `adapters/`, `stages/`, `errors/`, `pipeline/`
- [ ] Files named category: `category.jsonl`
- [ ] Each line is valid JSON
- [ ] Logs to correct directories
## Need Help?

- Check troubleshooting section above
- Search existing issues
- Create new issue with: OS, Python version, error message, steps to reproduce

Happy coding! 🚀
