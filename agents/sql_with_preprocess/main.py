
from langgraph.graph import END, StateGraph,START
from agents.search.main import arun as search
from agents.sql_with_preprocess.supervisor import make_supervisor_node as supervisor
from langchain_mistralai.chat_models import ChatMistralAI
from agents.sql_with_preprocess.sql_agent_subgraph import sql_agent_subgraph
from agents.chat_agent.main import get_response as chatbot
from agents.sql_with_preprocess.types import AgentState
from langchain.callbacks.tracers import LangChainTracer
from langchain_core.messages import HumanMessage,AIMessage,SystemMessage
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai.chat_models import ChatOpenAI

load_dotenv()   
# tracer = LangChainTracer("pr-charming-advertising-26")
from langchain_core.rate_limiters import InMemoryRateLimiter


async def create_graph()->StateGraph:
#     rate_limiter = InMemoryRateLimiter(
#     requests_per_second=0.02,  # <-- Super slow! We can only make a request once every 10 seconds!!
#     check_every_n_seconds=0.30,  # Wake up every 100 ms to check whether allowed to make a request,
#     max_bucket_size=10,  # Controls the maximum burst size.
# )
    # llm=ChatMistralAI(model='mistral-large-2411')
    # Qwen/Qwen2.5-72B-Instruct
    llm=ChatGoogleGenerativeAI(model='gemini-2.0-flash-exp')
    # llm=ChatOpenAI(model='meta-llama/Llama-3.3-70B-Instruct',temperature=0,base_url="https://api.hyperbolic.xyz/v1",api_key='eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJhZGl0aHlhYmFsYWdvbmkxMUBnbWFpbC5jb20ifQ.3kzGb2_LJoBucaEvozUIc8WGa5ud9W92GtDTQm9lZI4')
    # llm=ChatOpenAI(model='gpt-4o-mini')
    research_supervisor_node = await supervisor(llm, ["search", "sql","chatbot"])



    workflow = StateGraph(AgentState)
    workflow.add_node("supervisor", research_supervisor_node)
    workflow.add_node("search", search)
    workflow.add_node("sql", sql_agent_subgraph)
    workflow.add_node("chatbot",chatbot )




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
        attempts=0
    )
    
    # Run the graph with initial state
    result = await app.ainvoke(initial_state)    
    return result

# Optional: Add error handling

