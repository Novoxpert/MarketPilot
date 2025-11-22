from typing import Protocol, Any
from agentic.agent_types import AgentState


class ConditionCallable(Protocol):
  def __call__(
    self,
    state: AgentState,
  ) -> Any:
    ...
