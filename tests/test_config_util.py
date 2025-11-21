"""
Marketpilot Tests — Configuration Loader
=====================================

This module contains unit tests for validating the `load_config` function
defined in `src.utils.config_loader`. It ensures that YAML configuration
files are correctly parsed and return the expected Python dictionary
structure.

The tests make use of temporary files (via `pytest` fixtures) to simulate
real configuration files without depending on actual project files.

Features:
---------
- Creates a temporary YAML file dynamically for testing.
- Ensures that the loader correctly parses valid YAML.
- Validates the structure and data integrity of the loaded configuration.
- Confirms that nested keys and lists (e.g., tools) are handled properly.

Usage:
------
Run this test using `pytest` from the project root:

    $ pytest -q

Or run only this test file:

    $ pytest -q tests/test_config_loader.py

Example Output:
---------------
    ✓ Configuration file loaded successfully
    ✓ Keys and values match expected structure
    ✓ Tools list parsed correctly

Dependencies:
-------------
- pytest
- PyYAML
- pathlib
- src.utils.config_loader

"""

import pytest
import yaml
from pathlib import Path
from typing import Tuple, Dict, Any
from src.utils.config_loader import load_config


@pytest.fixture
def sample_config_file(tmp_path: Path) -> Tuple[Path, Dict[str, Any]]:
    """
    Create a temporary YAML configuration file for testing.

    Returns
    -------
    Tuple[Path, Dict[str, Any]]
        A tuple containing the path to the temporary YAML file and
        the dictionary of configuration data used to create it.
    """
    config_data: Dict[str, Any] = {
        "agent": {
            "name": "analyst",
            "version": "1.0",
            "description": "Test agent",
            "tools": [
                {"name": "llm_context_pack", "type": "Tool"}
            ]
        }
    }
    file_path: Path = tmp_path / "test_config.yml"
    with open(file_path, "w") as f:
        yaml.dump(config_data, f)
    return file_path, config_data


def test_load_config(sample_config_file: Tuple[Path, Dict[str, Any]]) -> None:
    """
    Test loading a YAML configuration file and verifying its structure and values.

    This test:
    ----------
    - Loads a sample YAML file using `load_config`.
    - Ensures that the returned object is a dictionary.
    - Checks that the "agent" section and its attributes match expected values.
    - Validates that the list of tools is properly parsed.
    """
    file_path, expected_config = sample_config_file
    config: Dict[str, Any] = load_config(file_path)

    # Check that config is a dict
    assert isinstance(config, dict)

    # Check top-level keys
    assert "agent" in config

    # Check agent definition
    agent: Dict[str, Any] = config["agent"]
    assert agent["name"] == expected_config["agent"]["name"]
    assert agent["version"] == expected_config["agent"]["version"]
    assert agent["description"] == expected_config["agent"]["description"]

    # Check tools
    tools: list[Dict[str, Any]] = agent.get("tools", [])
    assert len(tools) == 1
    assert tools[0]["name"] == "llm_context_pack"
    assert tools[0]["type"] == "Tool"
