"""
Marketpilot CLI — Run Agent
========================

This module implements the `run-agent` command for the Marketpilot Interactive CLI.
It simulates the execution of an agent’s workflow and provides visual feedback
through a progress bar using the `rich` library.

The purpose of this command is to represent the process of running a configured
agent — such as a data processor, reasoning engine, or workflow executor —
in a visually engaging way.

Features:
---------
- Displays a styled header with the selected agent name.
- Provides descriptive information about the agent’s execution steps.
- Shows a progress bar that simulates the agent’s task progression.
- Prints a success message upon completion.

Usage:
------
From the Marketpilot interactive console:

    λ run <target>/<name>

Or run directly as a Python module:

    $ python -m cli.commands.run_agent

Example Output:
---------------
───────────────────────────── Running Agent: my_agent ─────────────────────────────
The agent my_agent is about to execute its workflow.
It will load data, process features, and run its reasoning steps.

Please wait...
Running my_agent ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 100% 0:00:08
my_agent completed successfully!

Dependencies:
-------------
- rich
- time

"""

from marketpilot.cli.commands.run_agent import runner

from rich.console import Console
from rich.progress import track
from rich.padding import Padding
import time

console = Console()


def main(agent: str = "default") -> None:
    """
    Simulate running an agent and display its progress in the console.

    Parameters
    ----------
    agent : str, optional
        The name of the agent to run. Defaults to "default".

    Behavior
    --------
    - Prints a formatted header indicating the agent being executed.
    - Displays a short description of the agent’s actions.
    - Runs a simulated task loop with a progress bar for visual feedback.
    - Prints a success message upon completion.

    Example
    -------
    >>> main("data_agent")
    Running agent with progress visualization and success confirmation.
    """
    console.rule(f"[bold magenta]Running Agent: {agent}[/bold magenta]")
    
    description_text = (
        f"The agent [bold cyan]{agent}[/bold cyan] is about to execute its workflow.\n"
        "It will load data, process features, and run its reasoning steps.\n\n"
        "Please wait..."
    )
    console.print(Padding(description_text, (0, 0, 1, 0)))
    
    for _ in track(range(2), description=f"Running {agent} "):
        time.sleep(1)
        
    result = runner(agent)

    console.print(Padding(f"[green]{agent}[/green] {result}", (0, 0, 1, 0)))
