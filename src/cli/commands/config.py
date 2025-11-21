"""
Marketpilot CLI — Configuration Viewer
===================================

This module provides a command for displaying the contents of the Marketpilot
configuration file (`config.yml`) in a structured, colorized table format
using the `rich` library.

It is part of the Marketpilot Interactive CLI suite and is typically invoked via
the `show-config` command.

Features:
---------
- Loads configuration data from `config.yml`
- Displays nested sections and key-value pairs in a formatted table
- Provides styled console output with `rich`

Usage:
------
From the Marketpilot interactive console:

    λ show-config

Or run this module directly for debugging:

    $ python -m cli.commands.config

Expected Output:
----------------
A visually formatted table displaying each configuration section and its
corresponding keys and values.

Dependencies:
-------------
- rich
- PyYAML
- pathlib

"""

from rich.console import Console
from rich.table import Table
from rich.padding import Padding
import yaml
from pathlib import Path

console = Console()
CONFIG_PATH = Path("config.yml")


def show():
    """
    Display the contents of the Marketpilot configuration file in a rich-formatted table.

    The function:
    - Checks for the presence of `config.yml` in the current directory.
    - Parses it as YAML using `PyYAML`.
    - Displays each configuration section as a bold header.
    - Lists all key-value pairs under their respective sections.

    If `config.yml` is not found, a warning message is printed instead.
    """
    if not CONFIG_PATH.exists():
        console.print("[red]config.yml not found.[/red]")
        return

    with open(CONFIG_PATH, "r") as f:
        config = yaml.safe_load(f)

    table = Table(title="")
    table.add_column("Key", style="bold cyan")
    table.add_column("Value", style="green")

    for section, values in config.items():
        table.add_row(f"[bold]{section}[/bold]", "")
        for k, v in values.items():
            table.add_row(f"  {k}", str(v))

    console.rule(f"[bold cyan]Graph: Marketpilot Configuration[/bold cyan]")
    console.print(Padding(table, (1, 0, 1, 0)))
