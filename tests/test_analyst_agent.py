"""
Marketpilot Tests — Analyst Agent Configuration
============================================

This module contains unit tests for validating the configuration of the
`analyst.yml` agent definition used in the Marketpilot platform.

The tests ensure that the configuration file:
- Exists in the expected directory.
- Conforms to the required schema and field structure.
- Contains valid types for critical fields.
- Properly defines one or more associated tools.

These tests act as configuration integrity checks to prevent runtime
errors caused by malformed or incomplete YAML definitions.

Features:
---------
- Verifies the presence of `configs/agents/analyst.yml`.
- Checks that the top-level `agent` key exists.
- Validates mandatory agent fields such as `name`, `version`, and `tools`.
- Ensures proper data types for each configuration field.
- Confirms that each listed tool has the required keys and valid values.

Usage:
------
Run tests using `pytest` from the project root:

    $ pytest -q

Or to run only this specific test file:

    $ pytest -q tests/test_analyst_config.py

Example Output:
---------------
    ✓ analyst.yml file exists
    ✓ All required agent fields present
    ✓ Tools list properly defined
    ✓ Configuration types valid

Dependencies:
-------------
- pytest
- pathlib
- typing
- src.utils.config_loader

"""

from pathlib import Path
from typing import Dict, Any, List
from src.utils.config_loader import load_config

ANALYST_CONFIG_PATH = Path("configs/agents/analyst.yml")


def test_analyst_config_exists() -> None:
    """
    Ensure the `analyst.yml` configuration file exists in the expected path.
    """
    assert ANALYST_CONFIG_PATH.exists(), f"{ANALYST_CONFIG_PATH} does not exist."


def test_load_analyst_config() -> None:
    """
    Load the `analyst.yml` configuration and verify its structure and data types.

    Validates:
    ----------
    - The presence of the top-level `agent` key.
    - The existence of all required agent attributes:
        name, version, description, max_steps, logging_level, tools, decision_logic.
    - The correct data types for each attribute.
    - The presence and correctness of each defined tool entry.
    """
    config: Dict[str, Any] = load_config(ANALYST_CONFIG_PATH)

    # The agent definition should be under the top-level key "agent"
    assert "agent" in config, "Missing top-level 'agent' key"
    agent: Dict[str, Any] = config["agent"]

    # Top-level agent keys
    required_keys = [
        "name",
        "version",
        "description",
        "max_steps",
        "logging_level",
        "tools",
        "decision_logic",
    ]
    for key in required_keys:
        assert key in agent, f"Missing '{key}' key in agent config"

    # Validate types
    assert isinstance(agent["name"], str)
    assert isinstance(agent["version"], float)
    assert isinstance(agent["description"], str)
    assert isinstance(agent["max_steps"], int)
    assert isinstance(agent["logging_level"], str)
    assert isinstance(agent["decision_logic"], str)

    # Validate tools
    tools: List[Dict[str, Any]] = agent["tools"]
    assert len(tools) > 0, "Agent config should define at least one tool"

    for tool in tools:
        required_tool_keys = ["name", "type", "tool_ref", "description"]
        for key in required_tool_keys:
            assert key in tool, f"Tool missing '{key}'"
            assert isinstance(tool[key], str)
