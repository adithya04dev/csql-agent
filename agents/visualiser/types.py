from typing import TypedDict,Annotated
from langgraph.graph.message import add_messages

from langchain_core.messages import BaseMessage
from langchain_core.messages import AnyMessage


class VisualiserState(TypedDict):
    messages: Annotated[list[AnyMessage], add_messages]    
    code:str
    vattempts:int
    code_error:str
    result:str
