"""Story MP-002 Tests for config loader"""

import pytest
from config.config_loader import (
    load_schema,
    validate_data_columns,
    get_required_columns,
    ConfigError,
)


def test_load_price_schema():
    """Test loading price schema"""
    schema = load_schema("price")
    assert schema["type"] == "price"
    assert "symbol" in schema["required_columns"]
    assert "close" in schema["required_columns"]


def test_load_news_schema():
    """Test loading news schema"""
    schema = load_schema("news")
    assert schema["type"] == "news"
    assert "symbol" in schema["required_columns"]
    assert "data" in schema["required_columns"]


def test_load_fundamental_schema():
    """Test loading fundamental schema"""
    schema = load_schema("fundamental")
    assert schema["type"] == "fundamental"
    assert "symbol" in schema["required_columns"]
    assert "data" in schema["required_columns"]


def test_validate_valid_data():
    """Test validation with valid data"""
    data = {
        "symbol": "AAPL",
        "timestamp": "2024-01-01",
        "open": 100.0,
        "high": 105.0,
        "low": 99.0,
        "close": 103.0,
        "volume": 1000000,
    }
    assert validate_data_columns(data, "price") is True


def test_validate_missing_columns():
    """Test validation with missing columns"""
    data = {"symbol": "AAPL", "close": 103.0}  # Missing required columns

    with pytest.raises(ConfigError) as exc_info:
        validate_data_columns(data, "price")

    assert "Missing required columns" in str(exc_info.value)


def test_get_required_columns():
    """Test getting required columns"""
    columns = get_required_columns("price")
    assert "symbol" in columns
    assert "close" in columns
    assert len(columns) > 0


def test_invalid_schema_type():
    """Test loading invalid schema type"""
    with pytest.raises(ConfigError):
        load_schema("invalid_type")
