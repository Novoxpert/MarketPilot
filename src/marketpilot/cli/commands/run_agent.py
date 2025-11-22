from typing import Any

from marketpilot.agentic.agent_manager import AgentManager
from marketpilot.agentic.agent_types import AgentState

def runner(name: str) -> Any:

    manager = AgentManager()

    agent = manager.get_agent(name)

    if agent is None:
        raise RuntimeError("Agent not loaded!")

    state: AgentState = {
        "data": {"symbol": "AAPL"},
        "references": {},
        "messages": [],
        "log": []
    }

    result = agent(state)
    
    return result