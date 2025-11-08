"""
Configuration Loader for MarketPilot
Loads and validates YAML configuration files
"""

from pathlib import Path
from typing import Dict, Any, List
import yaml
from loguru import logger


class ConfigError(Exception):
    """Configuration error"""

    pass


def load_config(path: str) -> Dict[str, Any]:
    """
    Load and validate YAML configuration file

    Args:
        path: Path to YAML config file

    Returns:
        Validated configuration dictionary

    Raises:
        ConfigError: If config is invalid or missing required fields
    """
    config_path = Path(path)

    if not config_path.exists():
        raise ConfigError(f"Config file not found: {path}")

    try:
        with open(config_path, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)
    except yaml.YAMLError as e:
        raise ConfigError(f"Invalid YAML syntax in {path}: {e}")

    if not config:
        raise ConfigError(f"Empty config file: {path}")

    logger.info(f"Loaded config from {path}")
    return config


def load_schema(schema_type: str) -> Dict[str, Any]:
    """
    Load data schema (price, news, fundamental)

    Args:
        schema_type: Type of schema (price, news, fundamental)

    Returns:
        Schema dictionary
    """
    schema_path = Path(f"schemas/{schema_type}_schema.yaml")

    if not schema_path.exists():
        raise ConfigError(f"Schema not found: {schema_path}")

    return load_config(str(schema_path))


def validate_data_columns(data: Dict[str, Any], schema_type: str) -> bool:
    """
    Validate that data has required columns based on schema

    Args:
        data: Data dictionary to validate
        schema_type: Type of schema to validate against

    Returns:
        True if valid

    Raises:
        ConfigError: If validation fails
    """
    schema = load_schema(schema_type)
    required_columns = schema.get("required_columns", [])

    if not required_columns:
        logger.warning(f"No required columns defined in {schema_type} schema")
        return True

    # Check if data has columns key
    if "columns" in data:
        data_columns = data["columns"]
    elif isinstance(data, dict):
        data_columns = list(data.keys())
    else:
        raise ConfigError("Data must be a dictionary or have 'columns' key")

    # Find missing columns
    missing = [col for col in required_columns if col not in data_columns]

    if missing:
        error_msg = (
            f"Missing required columns in {schema_type} data: {missing}\n"
            f"Required: {required_columns}\n"
            f"Found: {data_columns}"
        )
        logger.error(error_msg)
        raise ConfigError(error_msg)

    logger.info(f"Validation passed for {schema_type} data")
    return True


def get_required_columns(schema_type: str) -> List[str]:
    """Get list of required columns for a schema type"""
    schema = load_schema(schema_type)
    return schema.get("required_columns", [])


def get_optional_columns(schema_type: str) -> List[str]:
    """Get list of optional columns for a schema type"""
    schema = load_schema(schema_type)
    return schema.get("optional_columns", [])


def get_data_types(schema_type: str) -> Dict[str, str]:
    """Get data types mapping for a schema type"""
    schema = load_schema(schema_type)
    return schema.get("data_types", {})
