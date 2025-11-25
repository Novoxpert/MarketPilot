"""
Configuration management utilities for Marketpilot.

Supports:
- Loading YAML configs
- Saving configs
- Optional schema validation
- Path helpers for agent/graph/tool/condition configs
"""

import yaml
from pathlib import Path
from typing import Dict, Any
from enum import Enum
from loguru import logger


class ConfigError(Exception):
    """Raised when configuration loading or validation fails."""

    pass


class ConfigType(Enum):
    """
    Enum representing the type of configuration.

    Attributes:
        AGENT: Agent configuration file
        GRAPH: Graph configuration file
        TOOL: Tool configuration file
        CONDITION: Conditional edge configuration file
    """

    AGENT = "agent"
    GRAPH = "graph"
    TOOL = "tool"
    CONDITION = "condition"
    DATA = "data"


CONFIG_DIR = Path("src/marketpilot/configs")


def make_config_path(config_type: ConfigType) -> Path:
    """Return directory path for a given config type."""
    return CONFIG_DIR / f"{config_type.value}s"


def make_file_path(config_type: ConfigType, file_name: str) -> Path:
    """Return full path of a config YAML file."""
    return make_config_path(config_type) / f"{file_name}.yml"


def load_config(path: str | Path) -> Dict[str, Any]:
    """
    Load a YAML configuration file and return its contents as a dictionary.

    Args:
        path: Path to the YAML config file.

    Returns:
        Parsed configuration dictionary.

    Raises:
        ConfigError: If the file is missing, empty, or has invalid YAML syntax.
    """
    config_path = Path(path)

    if not config_path.exists():
        raise ConfigError(f"Config file not found: {config_path}")

    try:
        with open(config_path, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)
    except yaml.YAMLError as e:
        raise ConfigError(f"Invalid YAML syntax in {config_path}: {e}")

    if not config:
        raise ConfigError(f"Empty config file: {config_path}")

    logger.info(f"Loaded config from {config_path}")
    return config


def save_config(config: Dict[str, Any], path: str | Path):
    """
    Save a dictionary as a YAML configuration file.

    Args:
        config (dict[str, Any]): Dictionary to save.
        file_path (Path, optional): Path to save the YAML file.
            Defaults to CONFIG_FILE.
    """
    with open(path, "w", encoding="utf-8") as f:
        yaml.dump(config, f, default_flow_style=False, allow_unicode=True)
    logger.info(f"Saved config to {path}")


SCHEMA_DIR = Path("src/marketpilot/data_farm/schemas")


def load_schema(schema_type: str) -> Dict[str, Any]:
    """Load schema file (price_schema.yml, news_schema.yml, ...)"""
    schema_file = SCHEMA_DIR / f"{schema_type}_schema.yml"
    return load_config(schema_file)
