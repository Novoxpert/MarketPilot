from typing import Dict, TypedDict, List, Any
from agentic.config_models import AgentConfig
from agentic.tool_protocol import ToolCallable
# from langchain.chat_models import ChatOpenAI
from langchain_core.messages import HumanMessage, AnyMessage # type: ignore
from typing import Annotated
import operator

class FeatureStoreState(TypedDict):
	messages: Annotated[list[AnyMessage], operator.add]
	data: Dict[str, Any]
	logs: List[str]

def feature_store_agent(
	state: FeatureStoreState,
	config: AgentConfig,
	tools: Dict[str, ToolCallable]
) -> FeatureStoreState:

	state.get("logs").append(f"Feature store executing")
	
	# llm = ChatOpenAI(model="gpt-4", temperature=0.2)

	# planning_prompt: List[AnyMessage] = [
	#     HumanMessage(content="Given the user query, generate a response using available tools."),
	#     *state["messages"]
	# ]
	# response = llm(planning_prompt)
	
	response = HumanMessage(content="stored all feature in the database")
	
	state["messages"].append(response)

	return state