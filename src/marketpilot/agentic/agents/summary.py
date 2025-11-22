from typing_extensions import TypedDict, Any, List, Dict
from agentic.config_models import AgentConfig
from agentic.tool_protocol import ToolCallable
# from langchain.chat_models import ChatOpenAI
from langchain_core.messages import HumanMessage, AnyMessage # type: ignore
from typing import Annotated
import operator

class SummaryState(TypedDict):
    messages: Annotated[list[AnyMessage], operator.add]
    data: Dict[str, Any]
    log: List[str]

def summary_agent(
    state: SummaryState, 
    config: AgentConfig,
    tools: Dict[str, ToolCallable]
) -> SummaryState:

    # llm = ChatOpenAI(model="gpt-4", temperature=0.2)

    planning_prompt = [ # type: ignore
        HumanMessage(content="Given the user query, generate a step-by-step plan using available tools."),
        *state["messages"]
    ]
    # response = llm(planning_prompt)
    response = HumanMessage(content="mock response")

    state["plan"] = response.content  # type: ignore
    print(f"[SUMMARY] Final Result: {state.get('result', 'N/A')}") # type: ignore
    return state
