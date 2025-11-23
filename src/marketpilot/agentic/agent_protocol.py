from typing import Protocol
from marketpilot.agentic.agent_types import AgentState


class AgentCallable(Protocol):
    def __call__(
        self,
        state: AgentState,
    ) -> AgentState:
        ...
