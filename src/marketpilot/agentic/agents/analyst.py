from typing import TypedDict, Dict, Annotated, Any, List
from agentic.config_models import AgentConfig
from agentic.tool_protocol import ToolCallable
from langchain.messages import AnyMessage
import operator

class AnalystState(TypedDict):
	messages: Annotated[list[AnyMessage], operator.add]
	data: Dict[str, Any]
	logs: List[str]


def analyst_agent(
	state: AnalystState,
	config: AgentConfig,
	tools: Dict[str, ToolCallable]
) -> AnalystState:

	state.get("logs").append(f"Analyst executing")

	if "context_pack" in tools:
		state.get("data.analyst", []).append(
			tools["context_pack"](
				symbol=state.get("data.symbol", {}),
				)
			)
	
	state \
  	.setdefault("data", {}) \
    .setdefault("analyst", []) \
    .append("analyst did some analyse stuff")

	return state
