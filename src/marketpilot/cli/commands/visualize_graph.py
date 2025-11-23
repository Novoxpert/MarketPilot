"""
Marketpilot CLI — Visualize Workflow (Dynamic)
===================================================================

This module implements the `visualize-graph` command for the Marketpilot Interactive CLI.
It dynamically loads a workflow definition from YAML and visualizes it as a
colorized, arrow-connected Rich tree.

The visualization highlights agentic relationships, data dependencies, and
control flow within the pipeline.

Features:
---------
- Dynamically reads workflow configuration from YAML files.
- Displays a styled header with the workflow name and version.
- Prints a short summary of the pipeline’s purpose and design.
- Renders a colorized, arrow-connected tree of agents.
- Clearly illustrates dependencies and data movement between agents.

Usage:
------
From the Marketpilot interactive console:

    λ visualize-graph trading_intelligence_workflow

Or run directly as a Python module:

    $ python -m cli.commands.visualize_graph configs/graphs/trading_intelligence_workflow.yml

Example Output:
---------------
────────────────────────────── Graph: trading_intelligence_workflow v1.0 ───────────────────────────────
A multi-agent trading pipeline that ingests market data, performs analysis,
assesses risk, identifies opportunities, and executes trades.

Agentic Workflow
load_data (DataLoader)
├── → analyst (Analyst)
│   ├── → risk_assessment (RiskAssessor)
│   │   └── → trader (Trader)
│   │       └── → feature_store (FeatureStore)
│   ├── → potential (OpportunityEvaluator)
│   │   └── → trader (Trader)
│   └── → feature_store (FeatureStore)
└── [End of Flow]

Dependencies:
-------------
- rich
- pathLib
- typing
"""

from pathlib import Path
from rich.console import Console
from rich.tree import Tree
from rich.padding import Padding
from typing import Dict, List, TypedDict
from marketpilot.utils.config_loader import load_config


class Node(TypedDict):
    name: str
    type: str
    role: str
    description: str


class Edge(TypedDict):
    from_: str
    to: str
    description: str


class WorkflowConfig(TypedDict, total=False):
    name: str
    version: str
    description: str
    nodes: List[Node]
    edges: List[Edge]


console = Console()


def main(graph_name: str) -> None:
    """
    Visualize a dynamically defined workflow graph using Rich tree rendering.

    Parameters
    ----------
    config_name : str
        name of the YAML configuration file (e.g., trading_intelligence_workflow)
    """
    # === Load configuration ===
    config_path: Path = Path(f"configs/graphs/{graph_name}.yml")
    config = load_config(config_path)
    graph_name = config.get("name", "unknown_workflow")
    version = config.get("version", "N/A")
    description = config.get("description", "No description provided.")
    nodes = config.get("nodes", [])
    edges = config.get("edges", [])

    # === Print header and description ===
    console.rule(
        f"[bold cyan]Graph: {graph_name}[/bold cyan] [green]v{version}[/green]"
    )
    console.print(Padding(description, (1, 0, 1, 0)))

    # === Build lookup maps ===
    node_map: Dict[str, Node] = {node["name"]: node for node in nodes}
    adjacency: Dict[str, List[str]] = {node["name"]: [] for node in nodes}

    for edge in edges:
        adjacency[edge["from"]].append(edge["to"])

    # Find root nodes (nodes that are not a target in any edge)
    root_nodes = [n for n in adjacency if all(e["to"] != n for e in edges)]

    # === Recursive tree builder ===
    from typing import Optional

    def build_subtree(
        parent_tree: Tree, node_name: str, visited: Optional[set[str]] = None
    ) -> None:
        if visited is None:
            visited = set()

        # Prevent infinite recursion
        if node_name in visited:
            return

        visited.add(node_name)
        node = node_map[node_name]
        # Add the current node
        label = f"[bold]{node_name}[/bold] ([magenta]{node['role']}[/magenta])"
        subtree = parent_tree.add(label)

        # Recurse to children
        for child in adjacency.get(node_name, []):
            build_subtree(subtree, child, visited.copy())

    # === Build and render the tree ===
    tree = Tree(
        "[bold cyan]Agentic Workflow[/bold cyan]", guide_style="bold bright_blue"
    )
    for root in root_nodes:
        build_subtree(tree, root)

    # Add end marker for clarity
    tree.add("[dim][End of Flow][/dim]")

    console.print(Padding(tree, (0, 0, 1, 0)))
