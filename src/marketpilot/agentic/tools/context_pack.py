from typing import Dict, Any, TypedDict

class ContextPackData(TypedDict):
  symbol: str
  news: str
  timestamp: str


def context_pack_tool(symbol: str, params: Dict[str, Any] = {}) -> ContextPackData:
  
  context_pack_data: ContextPackData = {
    "symbol": symbol,
    "news": "a mock news for {symbol}",
    "timestamp": "2025-11-16T12:00:00Z"
  }
  
  return context_pack_data
