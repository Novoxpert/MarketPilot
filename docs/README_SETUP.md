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
poetry run pre-commit install

# 5. Verify setup
poetry run pytest
```

---

## Get API Keys

1. **Alpha Vantage**: https://www.alphavantage.co/support/#api-key
2. **FMP**: https://site.financialmodelingprep.com/developer/docs
3. **Finnhub**: https://finnhub.io/register

Edit `.env` and replace placeholders with your actual keys.

---

## Common Commands

```bash
# Activate environment
poetry shell

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
- Test: `poetry run python -c "from config import config; print(config.alphavantage_api_key)"`

---

## Verify Installation

```bash
# Check all dependencies installed
poetry show

# Run all checks
poetry run pytest && poetry run black --check . && poetry run flake8 .
```

---

## Need Help?

- Check troubleshooting section above
- Search existing issues
- Create new issue with: OS, Python version, error message, steps to reproduce

Happy coding! 🚀