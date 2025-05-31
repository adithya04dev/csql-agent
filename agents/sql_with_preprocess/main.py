from langgraph.graph import END, START, StateGraph, MessagesState
from agents.search.main import arun as search
from agents.sql.main2 import arun as sql
from agents.sql_with_preprocess.supervisor import make_supervisor_node as supervisor
from langchain_mistralai.chat_models import ChatMistralAI
from agents.sql_with_preprocess.sql_agent_subgraph import sql_agent_subgraph
from agents.sql_with_preprocess.types1 import AgentState
from langchain.callbacks.tracers import LangChainTracer
from langchain_core.messages import HumanMessage,AIMessage,SystemMessage
from agents.visualiser.main2 import get_response
import os
from dotenv import load_dotenv
from agents.utils.llm_utils import get_llm

load_dotenv()   
# tracer = LangChainTracer("pr-charming-advertising-26")
from langchain_core.rate_limiters import InMemoryRateLimiter

# from langchain_groq import ChatGroq
from langchain.chat_models import init_chat_model

async def create_graph()->StateGraph:


    supervisor_model=os.getenv('SUPERVISOR_MODEL')
    llm=get_llm(supervisor_model)
    research_supervisor_node = await supervisor(llm, ["search", "sql","visualiser"])



    workflow = StateGraph(AgentState)
    workflow.add_node("supervisor", research_supervisor_node)
    workflow.add_node("search", search)
    workflow.add_node("sql", sql)
    # workflow.add_node("sql", sql_agent_subgraph)
    # workflow.add_node("chatbot",chatbot )
    # workflow.add_node("visualiser",run_visualiser )
    workflow.add_node("visualiser",get_response )



    workflow.add_edge(START, "supervisor")
    workflow.set_entry_point("supervisor")

    graph = workflow.compile(debug=True)
    return graph

async def runworkflow(query: str)->AgentState:
    # Initialize state with default values
    app=await create_graph()

    initial_state = AgentState(
        messages=[HumanMessage(content=query+" and dont execute and table name as hdata ")],
        query='',
        execution_choice=False,
        sql_query=None,
        sql_result="",
        relevant_sql_queries="",
        sql_error=False,
        referenced_values_in_table="",
        table_name=None,
        docs_schema="",
        change="",
        attempts=0,
        sequence=''
    )
    
    # Run the graph with initial state
    result = await app.ainvoke(initial_state)    
    return result

# Optional: Add error handling

