from typing import Protocol, Any


class ToolCallable(Protocol):
	def __call__(self, *args: Any, **kwargs: Any) -> Any:
		...
