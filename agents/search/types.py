from typing import Literal, TypedDict,Annotated
from langgraph.graph.message import add_messages

from langchain_core.messages import AnyMessage

class State(TypedDict):
    query: str
    table_name: str
    referenced_values_in_table: str
    messages: Annotated[list[AnyMessage], add_messages]