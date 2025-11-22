"""
Configuration management utilities for Marketpilot.

This module provides functions to:
- Load, save, and update YAML configuration files
- Generate file paths for agent and graph configurations using an Enum
"""

import yaml
from pathlib import Path
from typing import Any
from enum import Enum

# NOTE - Default project-level config file
CONFIG_FILE = Path("config.yml")


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

def make_config_path(config_type: ConfigType) -> Path:
    CONFIG_DIR = Path("src/marketpilot/configs")
    AGENT_DIR = CONFIG_DIR / "agents"
    GRAPH_DIR = CONFIG_DIR / "graphs"
    TOOL_DIR = CONFIG_DIR / "tools"
    CONDITION_DIR = CONFIG_DIR / "conditions"
    
    if config_type == ConfigType.AGENT:
        return AGENT_DIR
    elif config_type == ConfigType.GRAPH:
        return GRAPH_DIR
    elif config_type == ConfigType.TOOL:
        return TOOL_DIR
    elif config_type == ConfigType.CONDITION:
        return CONDITION_DIR
    else:
        raise ValueError(f"Invalid config type: {config_type}")
    

def make_file_path(config_type: ConfigType, file_name: str) -> Path:
    """
    Generate the full file path for a given configuration type and file name.

    Args:
        config_type (ConfigType): The type of configuration (AGENT or GRAPH or TOOL or CONDITION).
        file_name (str): The base name of the config file (without extension).

    Returns:
        Path: Full path to the configuration YAML file.

    Raises:
        ValueError: If an invalid ConfigType is provided.
    """
    CONFIG_DIR = Path("src/marketpilot/configs")
    AGENT_DIR = CONFIG_DIR / "agents"
    GRAPH_DIR = CONFIG_DIR / "graphs"
    TOOL_DIR = CONFIG_DIR / "tools"
    CONDITION_DIR = CONFIG_DIR / "conditions"

    if config_type == ConfigType.AGENT:
        return AGENT_DIR / f"{file_name}.yml"
    elif config_type == ConfigType.GRAPH:
        return GRAPH_DIR / f"{file_name}.yml"
    elif config_type == ConfigType.TOOL:
        return TOOL_DIR / f"{file_name}.yml"
    elif config_type == ConfigType.CONDITION:
        return CONDITION_DIR / f"{file_name}.yml"
    else:
        raise ValueError(f"Invalid config type: {config_type}")


def load_config(file_path: Path = CONFIG_FILE) -> dict[str, Any]:
    """
    Load a YAML configuration file into a dictionary.

    Args:
        file_path (Path, optional): Path to the YAML config file.
            Defaults to CONFIG_FILE.

    Returns:
        dict[str, Any]: Dictionary representation of the YAML configuration.
        Returns an empty dictionary if the file does not exist.
    """
    if not file_path.exists():
        return {}
    with open(file_path, "r") as f:
        return yaml.safe_load(f) or {}


def save_config(config: dict[str, Any], file_path: Path = CONFIG_FILE):
    """
    Save a dictionary as a YAML configuration file.

    Args:
        config (dict[str, Any]): Dictionary to save.
        file_path (Path, optional): Path to save the YAML file.
            Defaults to CONFIG_FILE.
    """
    with open(file_path, "w") as f:
        yaml.dump(config, f, default_flow_style=False)