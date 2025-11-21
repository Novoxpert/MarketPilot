from agentic.agent_types import AgentState

def should_discuss_more_condition(
  state: AgentState,
) -> str:

	content = state["messages"][-1].content.lower() # type: ignore
 
	if "risk_evaluator" in content:
		return "risk_evaluator"
	return "trader"