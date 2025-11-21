from typing import Dict, TypedDict, Any, List
from agentic.config_models import AgentConfig
from agentic.tool_protocol import ToolCallable
# from langchain.agents import Tool
# from langchain.tools import DuckDuckGoSearchRun
from langchain.messages import AnyMessage
from typing import Annotated
import operator

class RiskEvaluatorState(TypedDict):
	messages: Annotated[list[AnyMessage], operator.add]
	data: Dict[str, Any]
	logs: List[str]

def risk_evaluator_agent(
	state: RiskEvaluatorState,
	config: AgentConfig,
	tools: Dict[str, ToolCallable]
) -> RiskEvaluatorState:

	state.get("logs", []).append(f"Risk evaluator executing")
	
	# TODO - use query from older messages
	# query = state["messages"][-1].content  # type: ignore

	# search = DuckDuckGoSearchRun()
	# result = search.run(query)
	
	state \
		.setdefault("data", {}) \
		.setdefault("risk_assessment", []) \
		.append("risk assessment did some analyses stuff")

	return state