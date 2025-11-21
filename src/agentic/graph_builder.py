from langgraph.graph import StateGraph, START, END # type: ignore
from agentic.agent_types import AgentState
from agentic.node_registry import AGENT_REGISTRY, CONDITION_FN_REGISTRY
from utils.config_loader import load_config
from pathlib import Path

def build_dynamic_graph(graph_name: str):
	config_path: Path = Path(f"configs/graphs/{graph_name}.yml")
	workflow = load_config(config_path)
	
	graph = StateGraph(AgentState)

	for node in workflow["nodes"]:
		node_name = node["name"]

		if node_name not in AGENT_REGISTRY:
			raise ValueError(
				f"Agent '{node_name}' is defined in graph config "
				f"but not registered in AGENT_REGISTRY."
			)

		agent_fn = AGENT_REGISTRY[node_name]
		graph.add_node(node_name, agent_fn) # type: ignore

	for edge in workflow["edges"]:
		frm, to = edge["from"], edge["to"]
		graph.add_edge(frm, to)
	
	if "conditional_edges" in workflow:
		for cond in workflow["conditional_edges"]:
			fn = CONDITION_FN_REGISTRY[cond["condition"]]
			graph.add_conditional_edges(
				cond["from"],
				fn,
				cond["to"]
			)

	first_node = workflow["nodes"][0]["name"]
	graph.add_edge(START, first_node)

	all_nodes = {n["name"] for n in workflow["nodes"]}
	from_nodes = {e["from"] for e in workflow["edges"]}
	terminal_nodes = all_nodes - from_nodes

	for terminal in terminal_nodes:
		graph.add_edge(terminal, END)

	return graph.compile() # type: ignore