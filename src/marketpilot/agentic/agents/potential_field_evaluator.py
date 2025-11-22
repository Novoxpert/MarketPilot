from typing import Dict, TypedDict, Any, List
from agentic.config_models import AgentConfig
from agentic.tool_protocol import ToolCallable
from langchain.messages import AnyMessage, HumanMessage
from typing import Annotated
import operator

class PotentialState(TypedDict):
	messages: Annotated[list[AnyMessage], operator.add]
	data: Dict[str, Any]
	logs: List[str]

def potential_field_evaluator_agent(
	state: PotentialState,
	config: AgentConfig,
	tools: Dict[str, ToolCallable]
) -> PotentialState:

	state.get("logs").append(f"Potential field evaluator executing")
	
	# TODO - use required contents from older messages 
	# content = state["messages"][-1].content.lower() # type: ignore
	
	state \
  	.setdefault("data", {}) \
    .setdefault("potential", []) \
    .append("potential did some analyses stuff")
	
	if len(state.setdefault("data", {}).setdefault("risk_assessment", [])) < 2:
		state["messages"] \
    	.append(
       	HumanMessage(content="it's better to assess some risks using risk_evaluator")
      )
	else:
		state["messages"] \
    	.append(
       	HumanMessage(content="lets move forward to trader agent to see the final result")
      )
			
	return state