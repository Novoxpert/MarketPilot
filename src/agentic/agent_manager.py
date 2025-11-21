import importlib
from typing import Dict, Optional, List, Callable, cast

from utils.config_loader import ConfigType, make_config_path, load_config

from agentic.config_models import AgentConfig, ToolConfig, ConditionConfig
from agentic.agent_types import AgentState
from agentic.tool_protocol import ToolCallable
from agentic.agent_protocol import AgentCallable
from agentic.condition_protocol import ConditionCallable

class AgentManager:

    def __init__(self) -> None:
      self.agent_configs: Dict[str, AgentConfig] = {}
      self.tool_configs: Dict[str, ToolConfig] = {}
      self.condition_configs: Dict[str, ConditionConfig] = {}

      self.tools: Dict[str, ToolCallable] = {}
      self.agents: Dict[str, AgentCallable] = {}
      self.conditions: Dict[str, ConditionCallable] = {}

      self._load_agent_configs()
      self._load_tool_configs()
      self._load_condition_configs()

      self._import_tools()
      self._import_agents()
      self._import_conditions()

    def _load_agent_configs(self) -> None:
      AGENTS_CONFIG_DIR = make_config_path(ConfigType.AGENT)
      for file in AGENTS_CONFIG_DIR.glob("*.yml"):
        raw = load_config(file)

        agent_cfg = AgentConfig(**raw["agent"])
        self.agent_configs[agent_cfg.name] = agent_cfg
        
    def _load_condition_configs(self) -> None:
      CONDITIONS_CONFIG_DIR = make_config_path(ConfigType.CONDITION)
      for file in CONDITIONS_CONFIG_DIR.glob("*.yml"):
        raw = load_config(file)

        condition_cfg = ConditionConfig(**raw["condition"])
        self.condition_configs[condition_cfg.name] = condition_cfg

    def _load_tool_configs(self) -> None:
      TOOLS_CONFIG_DIR = make_config_path(ConfigType.TOOL)
      for file in TOOLS_CONFIG_DIR.glob("*.yml"):
        raw = load_config(file)

        tool_cfg = ToolConfig(**raw["tool"])
        self.tool_configs[tool_cfg.name] = tool_cfg

    def _import_tools(self) -> None:
      for tool_name, _cfg in self.tool_configs.items():
        module_path = f"agentic.tools.{tool_name}"

        try:
          module = importlib.import_module(module_path)
        except ModuleNotFoundError:
          print(f"[WARN] Missing tool module: {module_path}")
          continue

        fn = getattr(module, f"{tool_name}_tool", None)

        if callable(fn):
          self.tools[tool_name] = fn
        else:
          print(f"[WARN] Tool function `{tool_name}_tool` not found in {module_path}")

    def _import_agents(self) -> None:
      for agent_name, cfg in self.agent_configs.items():
        role_module = f"agentic.agents.{cfg.name}"

        try:
          module = importlib.import_module(role_module)
        except ModuleNotFoundError:
          print(f"[WARN] Agent module missing: {role_module}")
          continue

        fn = getattr(module, f"{cfg.name}_agent", None)

        if callable(fn):
          typed_raw = cast(Callable[[AgentState, AgentConfig, Dict[str, ToolCallable]], AgentState], fn)
          wrapped = self._wrap_agent(typed_raw, cfg)
          self.agents[agent_name] = wrapped
        else:
          print(f"[WARN] Agent function `{cfg.name}_agent` missing in {role_module}")
          
    def _import_conditions(self) -> None:
      for condition_name, _cfg in self.condition_configs.items():
        module_path = f"agentic.conditions.{condition_name}"

        try:
          module = importlib.import_module(module_path)
        except ModuleNotFoundError:
          print(f"[WARN] Missing condition module: {module_path}")
          continue

        fn = getattr(module, f"{condition_name}_condition", None)

        if callable(fn):
          self.conditions[condition_name] = fn
        else:
          print(f"[WARN] Condition function `{condition_name}_condition` not found in {module_path}")

    def _wrap_agent(
      self,
      fn: Callable[[AgentState, AgentConfig, Dict[str, ToolCallable]], AgentState],
      config: AgentConfig,
    ) -> AgentCallable:

      def wrapped(state: AgentState) -> AgentState:
        tool_map: Dict[str, ToolCallable] = {}

        for t in config.tools:
          if t.tool_ref in self.tools:
            tool_map[t.name] = self.tools[t.tool_ref]

        return fn(state, config, tool_map)

      return wrapped

    def get_agent(self, name: str) -> Optional[AgentCallable]:
      return self.agents.get(name)

    def list_agents(self) -> List[str]:
      return list(self.agents.keys())
    
    def get_condition(self, name: str) -> Optional[ConditionCallable]:
      return self.conditions.get(name)
    
    def list_conditions(self) -> List[str]:
      return list(self.conditions.keys())
