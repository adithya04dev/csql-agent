from typing import Literal, TypedDict,Annotated
from langgraph.graph.message import add_messages
from langchain_core.messages import AnyMessage

class AgentState(TypedDict):
    messages: Annotated[list[AnyMessage], add_messages]    
    query: str
    execution_choice: bool
    sql_query:str
    sql_result:str 
    relevant_sql_queries:str
    sql_error:bool

    referenced_values_in_table:str
    table_name:str
    docs_schema:str
    search_result:str
    
    change:bool
    attempts:int



