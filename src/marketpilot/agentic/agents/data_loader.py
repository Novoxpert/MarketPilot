from typing import Dict, TypedDict
from agentic.config_models import AgentConfig
from agentic.tool_protocol import ToolCallable
# from langchain.vectorstores import FAISS
# from langchain.embeddings import OpenAIEmbeddings
# from langchain.schema import Document
from langchain.messages import AnyMessage
from typing import Annotated, Any, List
import operator

class DataLoaderState(TypedDict):
	messages: Annotated[list[AnyMessage], operator.add]
	data: Dict[str, Any]
	logs: List[str]

def data_loader_agent(
	state: DataLoaderState,
	config: AgentConfig,
	tools: Dict[str, ToolCallable]
) -> DataLoaderState:
	
	state.get("logs").append(f"Data loader executing")
	
	# query = state["messages"][-1].content

	# vectorstore = FAISS.load_local("vectorstore_index", OpenAIEmbeddings())
	# docs: list[Document] = vectorstore.similarity_search(query, k=3)

	# state["documents"] = [doc.page_content for doc in docs]
			
	state \
		.setdefault("data", {}) \
		.setdefault("data_loader", []) \
		.append("fetched some raw data from remote")

	return state