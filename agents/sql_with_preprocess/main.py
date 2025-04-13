
from langgraph.graph import END, START, StateGraph, MessagesState
from agents.search.main import arun as search
from agents.sql_with_preprocess.supervisor import make_supervisor_node as supervisor
from langchain_mistralai.chat_models import ChatMistralAI
from agents.sql_with_preprocess.sql_agent_subgraph import sql_agent_subgraph
from agents.sql_with_preprocess.types1 import AgentState
from langchain.callbacks.tracers import LangChainTracer
from langchain_core.messages import HumanMessage,AIMessage,SystemMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai.chat_models import ChatOpenAI
# from agents.visualiser.main import run_visualiser
from agents.visualiser.main2 import get_response
from langchain_aws import ChatBedrock

from dotenv import load_dotenv

load_dotenv()   
# tracer = LangChainTracer("pr-charming-advertising-26")
from langchain_core.rate_limiters import InMemoryRateLimiter

# from langchain_groq import ChatGroq

async def create_graph()->StateGraph:
    rate_limiter = InMemoryRateLimiter(
    requests_per_second=1,  # <-- Super slow! We can only make a request once every 10 seconds!!
    check_every_n_seconds=0.1,  # Wake up every 100 ms to check whether allowed to make a request,
    max_bucket_size=100,  # Controls the maximum burst size.
)
    # llm=ChatMistralAI(model='mistral-large-2411')
    # Qwen/Qwen2.5-72B-Instruct
    # llm=ChatGoogleGenerativeAI(model='gemini-2.0-flash-exp',temperature=0)
    # llm=ChatGroq(model='llama-3.3-70b-versatile')
    # llm=ChatGoogleGenerativeAI(model='gemini-1.5-flash')
    # llm=ChatOpenAI(model='meta-llama/Llama-3.3-70B-Instruct',temperature=0,base_url="https://api.hyperbolic.xyz/v1",api_key='eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJhZGl0aHlhYmFsYWdvbmkxMUBnbWFpbC5jb20ifQ.3kzGb2_LJoBucaEvozUIc8WGa5ud9W92GtDTQm9lZI4')
    # llm=ChatOpenAI(model='o3-mini',reasoning_effort='high')
    # llm=ChatOpenAI(model='openrouter/quasar-alpha', base_url="https://openrouter.ai/api/v1",api_key='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')
    # llm = ChatBedrock(model_id="us.anthropic.claude-3-5-sonnet-20241022-v2:0")
    llm=ChatGoogleGenerativeAI(model='gemini-2.5-pro-preview-03-25',temperature=0.1)
    # llm = ChatBedrock(model_id="us.anthropic.claude-3-5-haiku-20241022-v1:0")
    research_supervisor_node = await supervisor(llm, ["search", "sql","visualiser"])



    workflow = StateGraph(AgentState)
    workflow.add_node("supervisor", research_supervisor_node)
    workflow.add_node("search", search)
    workflow.add_node("sql", sql_agent_subgraph)
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

