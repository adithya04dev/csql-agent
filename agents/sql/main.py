
from langgraph.graph import END, START, StateGraph, MessagesState
from langgraph.graph import StateGraph
from agents.sql.tester import sql_query_tester
# from .types import State
from typing import Annotated, Literal, TypedDict

from agents.sql_with_preprocess.types1 import AgentState
from agents.sql.sql_writer import sql_writer
from agents.sql.sql_writer import get_query
async def router(state: AgentState) :
    if state["sql_error"]==False   or state['attempts']>3:
        
        return END
    else:
        return "sql_writer"

    # return state["next"]


workflow = StateGraph(AgentState)
# workflow.add_node("get_query", get_query)

workflow.add_node("sql_writer", sql_writer)
workflow.add_node("sql_query_tester", sql_query_tester)



workflow.add_edge(START, "sql_writer")
# workflow.add_edge("get_query", "sql_writer")

workflow.add_edge("sql_writer", "sql_query_tester")
workflow.add_conditional_edges("sql_query_tester", router)


graph = workflow.compile()