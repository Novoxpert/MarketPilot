"""
Marketpilot CLI — List Targets
===========================

This module provides the implementation of the `list-targets` command for the
Marketpilot Interactive CLI. It displays all available components — agents, tools,
and graphs — in a formatted table with their names, types, and brief descriptions.

It uses the shared configuration loader utility (`utils.config_loader`) to load
YAML configuration files for each component type.

Features:
---------
- Dynamically loads all defined agents, tools, and graphs from configuration files.
- Displays a concise summary table with color-coded columns.
- Truncates long descriptions for a cleaner view.
- Integrates with the Rich library for visually appealing CLI output.

Usage:
------
From the Marketpilot interactive console:

    λ list-targets

Or directly as a Python module:

    $ python -m cli.commands.list_targets

Example Output:
---------------
─────────────────────────────── Available Components ───────────────────────────────
Name               Type       Description
────────────────── ────────── ─────────────────────────────────────────────────────
data_agent         Agent      Handles data ingestion from CSV and API sources...
text_tool          Tool       Performs NLP preprocessing and text tokenization...
workflow_graph     Graph      Executes a pipeline of data transformations...

Dependencies:
-------------
- rich
- pathlib
- PyYAML (via config_loader)

"""

from pathlib import Path
from typing import Dict, Any, List
from rich.console import Console
from rich.table import Table
from rich.padding import Padding
from utils.config_loader import load_config, ConfigType, make_config_path

console = Console()


def main() -> None:
    """
    Display all registered agents, tools, and graphs in a formatted table.

    This function:
    - Loads configurations for each type (agent, tool, graph) using `load_config()`.
    - Extracts metadata such as name, type, and description.
    - Truncates descriptions to 70 characters for readability.
    - Prints the information in a Rich-styled table.

    The function depends on configuration files stored under paths
    defined by `make_config_path()` for each `ConfigType`.
    """
    table = Table(title="")
    table.add_column("Name", style="cyan", no_wrap=True)
    table.add_column("Type", style="green")
    table.add_column("Description", style="magenta")

    # Helper to load all configs in a folder
    def load_configs(config_type: ConfigType) -> List[Dict[str, Any]]:
        folder_path: Path = make_config_path(config_type)
        folder: Path = folder_path.parent if folder_path.suffix else folder_path  # ensure folder path
        if not folder.exists():
            return []
        configs: List[Dict[str, Any]] = []
        for file_path in folder.glob("*.yml"):
            data = load_config(file_path)
            configs.append(data)
        return configs

    # List agents
    for agent_config in load_configs(ConfigType.AGENT):
        agent_data: Dict[str, Any] = agent_config.get("agent", {})
        if agent_data:
            table.add_row(
                agent_data.get("name", "Unknown"),
                "Agent",
                (agent_data.get("description") or "").split("\n")[0][:70] + "..."
            )

    # List tools
    for tool_config in load_configs(ConfigType.TOOL):
        tool_data: Dict[str, Any] = tool_config.get("tool", {})
        name = tool_data.get("name", "Unknown")
        description = (tool_data.get("description") or "").split("\n")[0][:70] + "..."
        table.add_row(name, "Tool", description)

    # List graphs
    for graph_config in load_configs(ConfigType.GRAPH):
        name = graph_config.get("name", "Unknown")
        description = (graph_config.get("description") or "").split("\n")[0][:70] + "..."
        table.add_row(name, "Graph", description)

    console.rule(f"[bold cyan]Available Components[/bold cyan]")
    console.print(Padding(table, (1, 0, 1, 0)))
