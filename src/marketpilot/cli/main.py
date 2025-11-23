"""
Marketpilot Interactive CLI
========================

This module provides the interactive command-line interface for the Marketpilot platform.
It uses the `rich` library for enhanced console output and supports a variety of commands
to interact with agents, tools, and graph workflows.

Features:
---------
- Interactive REPL-style prompt for executing commands.
- Rich-formatted output with colors, panels, and padding.
- Supports commands for:
    • Running agents, tools, or workflows (`run-agent <name>`)
    • Visualizing graph definitions (`visualize-graph <name>`)
    • Listing available agents, tools, and graphs (`list-targets`)
    • Displaying configuration (`show-config`)
    • Clearing the console (`clear`)
    • Displaying help (`help`)
    • Exiting the CLI (`exit`)

Usage:
------
Run the CLI entry point (usually installed via setup.py) or execute directly:

    $ marketpilot-cli

Example session:
----------------
    λ help
    λ list-targets
    λ run-agent my_agent
    λ visualize-graph sample_workflow
    λ exit

Modules imported:
-----------------
- `rich.console.Console` for styled console output.
- `rich.prompt.Prompt` for interactive command input.
- `cli.commands` for invoking subcommands.

"""

from rich.console import Console
from rich.prompt import Prompt
from rich.panel import Panel
from rich.padding import Padding
from marketpilot.cli.commands import run_target, visualize_graph, list_targets, config

console = Console()


def show_banner():
    """Display a welcome banner at the start of the interactive session."""
    console.print(
        Padding(
            Panel.fit(
                "[bold cyan]Welcome to Marketpilot Interactive CLI[/bold cyan]\n"
                "Type [green]help[/green] to see available commands or [red]exit[/red] to quit.",
                border_style="magenta",
            ),
            (0, 0, 1, 0),
        )
    )


def show_help():
    """Display the help panel listing all available CLI commands."""
    console.print(
        Padding(
            Panel.fit(
                """[bold yellow]Available Commands:[/bold yellow]
  [cyan]run <target>/<name>[/cyan]     → Run an agent, tool, or graph workflow by specifying its name
  [cyan]visualize-graph <name>[/cyan]  → Visualize a graph / workflow definition
  [cyan]list-targets[/cyan]            → List all available agents, tools, and graphs
  [cyan]show-config[/cyan]             → Display current configuration
  [cyan]clear[/cyan]                   → Clear the console
  [cyan]help[/cyan]                    → Show this help menu
  [cyan]exit[/cyan]                    → Quit the shell""",
                border_style="yellow",
            ),
            (0, 0, 1, 0),
        )
    )


def main():
    """Start the Marketpilot interactive console and handle user commands."""
    show_banner()

    while True:
        try:
            command = Prompt.ask(
                "[bold magenta]λ[/bold magenta]", default="help"
            ).strip()

            if not command:
                continue

            if command in ["exit", "quit"]:
                break

            elif command == "help":
                show_help()

            elif command == "list-targets":
                list_targets.main()

            elif command == "clear":
                console.clear()

            elif command.startswith("run"):
                parts = command.split()
                agent = parts[1] if len(parts) > 1 else "default"
                run_target.main(agent=agent)

            elif command.startswith("visualize-graph"):
                parts = command.split()
                graph = parts[1] if len(parts) > 1 else "default"
                visualize_graph.main(graph_name=graph)

            elif command == "show-config":
                config.show()

            else:
                console.print(
                    Padding(
                        f"[red]Unknown command:[/red] {command}. Type [green]help[/green] for options.",
                        (0, 0, 1, 0),
                    )
                )

        except KeyboardInterrupt:
            console.print(
                Padding(
                    "\n[bold red]Interrupted. Type 'exit' to quit.[/bold red]",
                    (0, 0, 1, 0),
                )
            )
        except Exception as e:
            console.print(Padding(f"[bold red]Error:[/bold red] {e}", (0, 0, 1, 0)))


if __name__ == "__main__":
    main()
