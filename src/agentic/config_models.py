from typing import List, Optional
from pydantic import BaseModel


class ToolRef(BaseModel):
    name: str
    type: str
    tool_ref: str
    description: Optional[str] = None


class AgentConfig(BaseModel):
    name: str
    version: float
    description: str
    max_steps: int
    logging_level: str
    tools: List[ToolRef]
    decision_logic: Optional[str] = None


class ToolConfig(BaseModel):
    name: str
    type: str
    version: float
    description: str
    

class ConditionConfig(BaseModel):
    name: str
    type: str
    version: float
    description: str
