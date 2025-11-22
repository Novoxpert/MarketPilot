from typing import Dict, TypedDict, Any, List
from agentic.config_models import AgentConfig
from agentic.tool_protocol import ToolCallable
# from langchain.chat_models import ChatOpenAI
from langchain_core.messages import HumanMessage, AnyMessage
from typing import Annotated
import operator

class TraderState(TypedDict):
	messages: Annotated[list[AnyMessage], operator.add]
	data: Dict[str, Any]
	logs: List[str]

def trader_agent(
	state: TraderState,
	config: AgentConfig,
	tools: Dict[str, ToolCallable]
) -> TraderState:

	state.get("logs").append(f"Trader executing")
	
	# TODO - create your own llm based agent
	
	# llm = ChatOpenAI(model="gpt-4", temperature=0.3)
	
	# messages = state["messages"]
	# response = llm(messages)
	
	response = HumanMessage(content="Final result based on all analyses")

	state["messages"].append(response) # type: ignore

	return state