from typing import Dict

from agentic.agent_protocol import AgentCallable
from agentic.condition_protocol import ConditionCallable
from agentic.agent_manager import AgentManager

manager = AgentManager()

agents_list = manager.list_agents()

AGENT_REGISTRY: Dict[str, AgentCallable] = {
	name: agent
	for name in agents_list
	if (agent := manager.get_agent(name)) is not None
}

condition_list = manager.list_conditions()

CONDITION_FN_REGISTRY: Dict[str, ConditionCallable] = {
	name: condition
	for name in condition_list
	if (condition := manager.get_condition(name)) is not None
}