"""Example usage of config loader"""
from data_farm.config.config_loader import (
    load_schema,
    validate_data_columns,
    get_required_columns,
)

# Load schema
price_schema = load_schema("price")
print("Price schema:", price_schema)

# Get required columns
required = get_required_columns("price")
print("Required columns:", required)

# Validate data
price_data = {
    "symbol": "AAPL",
    "timestamp": "2024-01-01",
    "open": 150.0,
    "high": 155.0,
    "low": 149.0,
    "close": 154.0,
    "volume": 50000000,
}

try:
    validate_data_columns(price_data, "price")
    print("✅ Data is valid!")
except Exception as e:
    print(f"❌ Validation failed: {e}")

# Example with missing columns (will fail)
invalid_data = {"symbol": "AAPL", "data": {}}  # Missing startdate and enddate

try:
    validate_data_columns(invalid_data, "price")
except Exception as e:
    print(f"❌ Expected error: {e}")


# Example with news data
print("\n--- News Data Example ---")
news_data = {
    "symbol": "AAPL",
    "startdate": "2024-01-01",
    "enddate": "2024-01-31",
    "data": [{"title": "Apple announces...", "source": "Reuters"}],
}

try:
    validate_data_columns(news_data, "news")
    print("✅ News data is valid!")
except Exception as e:
    print(f"❌ Validation failed: {e}")


# Example with fundamental data
print("\n--- Fundamental Data Example ---")
fundamental_data = {
    "symbol": "AAPL",
    "startdate": "2024-01-01",
    "enddate": "2024-03-31",
    "data": {"revenue": 123.4, "net_income": 45.6},
}

try:
    validate_data_columns(fundamental_data, "fundamental")
    print("✅ Fundamental data is valid!")
except Exception as e:
    print(f"❌ Validation failed: {e}")