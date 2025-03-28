from langchain_core.messages import SystemMessage
from langchain_openai.chat_models import ChatOpenAI
# from langgraph.prebuilt.chat_agent_executor import create_tool_calling_executor
from langchain_mistralai.chat_models import ChatMistralAI
from dotenv import load_dotenv
from agents.tools.search_vectordb import tool
from langgraph.types import Command
from langchain_core.messages import SystemMessage,AIMessage,HumanMessage,ToolMessage
from agents.sql_with_preprocess.types1 import AgentState
from langchain_google_genai import ChatGoogleGenerativeAI
load_dotenv()
from langgraph.prebuilt import create_react_agent
from langsmith import Client
from langchain.callbacks.tracers import LangChainTracer
from langchain.callbacks.manager import CallbackManager
# Add these near your other environment variable loads
import uuid
from langchain_core.rate_limiters import InMemoryRateLimiter
from langchain_together import ChatTogether
from agents.tools.search_vectordb import tool, SearchPair
from langchain_aws import ChatBedrock

async def arun(state: AgentState):
    
    # model = ChatMistralAI(      model='mistral-small-latest',    )

    # model=ChatGoogleGenerativeAI(model='gemini-1.5-flash')
    rate_limiter = InMemoryRateLimiter(
    requests_per_second=1,  # <-- Super slow! We can only make a request once every 10 seconds!!
    check_every_n_seconds=0.30,  # Wake up every 100 ms to check whether allowed to make a request,
    max_bucket_size=10,  # Controls the maximum burst size.
)
    model = ChatMistralAI(model='mistral-large-2411')
    # model = ChatBedrock(model_id="us.anthropic.claude-3-5-haiku-20241022-v1:0")

    # model=ChatGoogleGenerativeAI(model='gemini-2.0-flash-001')
#     model = ChatTogether(
#     # together_api_key="YOUR_API_KEY",
#     model="Qwen/Qwen2.5-72B-Instruct-Turbo",
#     api_key='29e062d0a46153ddc46e8920e276262852db8028456e8fa5aa47d1bd4724ff33'
# )

    # model=ChatOpenAI(model='gpt-4o-mini')
    # model=ChatOpenAI(model='meta-llama/Llama-3.3-70B-Instruct',temperature=0,base_url="https://api.hyperbolic.xyz/v1",api_key='eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJhZGl0aHlhYmFsYWdvbmkxMUBnbWFpbC5jb20ifQ.3kzGb2_LJoBucaEvozUIc8WGa5ud9W92GtDTQm9lZI4')


    # agent = create_tool_calling_agent(model, tools, prompt)
    # agent_executor = AgentExecutor(agent=agent, tools=tools)

    messages=SystemMessage(
        content="""You are a Search Agent specialized in cricket analytics, working as part of a multi-agent system.
Your primary role is to help standardize and validate cricket-related terms by matching user inputs to actual database values.

You will be given user conversation based on that u need to interpret and find correct matching values in databse for a query..
You are just an search agent..


Databases and its Schema:
Table: hdata_2501 
Columns: player, team, dismissal, ground, country, competition, bat_hand, bowl_style(specifies in detail), bowl_kind(broadly classifies like spin or pace), line, length, shot

Columns: player, team, dismissal, ground, country, competition, bat_hand, bowl_style(specifies in detail), bowl_kind(broadly classifies like spin or pace), line, length, shot

Your Process:
1. Analyze user queries to identify cricket-related terms that need validation
2. Use the provided search tool to find potential matches in the database
3. After that the search tool returns multiple similar values:
   - Analyze each returned value carefully
   - Consider the context of the user's query
   - Use cricket domain knowledge to select the most appropriate match
4. Return results in a clean JSON format compulsory:
   {
        "searched_term1": ["actual_database_value1","actual_database_column1"],
          "searched_term2":[ "actual_database_value2","actual_database_column2"]

   }

Guidelines:
- Always use the search tool to verify terms
- When multiple similar results are found:
  -Use cricket domain knowledge to select the most appropriate match or matches .
  -U may also reject and leave blank , if u dont find appropriate match.
  -U can also return more than one matches if u find it appropriate.
- If truly uncertain between multiple matches, return what u think might be most popular ones.
-If no specific valueS is mentioned of a column type dont search..
  it will be handled by sql agent dont worry about it

Examples:

User Conversation: 


"matches where stev smit played a coverdrives against fast bowling at MCG"

Search Process:
1. First, identify all terms needing validation:
   - Player: "stev smit"
   - Shot: "coverdrives"
   - Bowl_kind: "fast"
   - Ground: "MCG"

2. Search Results Analysis:
   - Player "Smith" returns multiple matches:
     * "Graeme Smith"
     * "Steven Smith"
    * other names
     → Select "Steve Smith" (as it's based on the context)
   
   - Ground "MCG" returns:
     * "Melbourne Cricket Ground"
     * "Sydney Cricket Ground"
     *other
     → Select "Melbourne Cricket Ground" 
   
   - Shot type matches:
     * "cover drive"
     → Direct match found
   
   - Bowl_kind "fast" matches:
     * "Fast"
     * "Medium Fast"
     → Select "Fast" (as query specifically mentioned fast bowling)
  3.Use cricket knowledge understanding to select the most appropriate ones based on the context and return results 
  in json  format

Final Output:
{
    "stev smit": ["Steve Smith","player" ],
    "MCG": ["Melbourne Cricket Ground","ground"],
    "coverdrives": ["cover drive","shot"],
    "fast": ["Fast","bowl_kind"]
}

Remember: 
-Your role is not just to search, but to intelligently interpret and standardize cricket terms for accurate database queries.
-Use the necessary tools to search..dont give on your own previous knowledge.
-you will be given a whole cnversation based on that understad what u need to interpret and search and standardise.
-another point is to rely solely on the information provided by the user; you cannot communicate with them again.
-If no specific valueS is mentioned of a column type dont search..
  it will be handled by sql agent dont worry about it
-You are just an search agent part of an ai multi-agents system..u just need to search and add to conversation and not write sql queries that will be handled by sql agent dont worry about it!   
""")
        
    agent = create_react_agent(model=model, tools=[tool],state_modifier=messages)


    result = await agent.ainvoke({'messages':state['messages']})
    response =[]
    response.append(AIMessage(content=f"Search Agent Response: \n{result["messages"][-1].content.replace('`', '')}\n ")),
    if len(state['messages'])<3:
        
      search_pair = SearchPair(
      search_value=state['messages'][0].content,
      column_name='sql_queries',
      table_name='hdata_2501'  
  )
      state['relevant_sql_queries'] = await tool._arun([search_pair],limit=4)
      response.append(HumanMessage(content=f""" 

          Some Similar  SQL Queries in database after searching is: {state['relevant_sql_queries']}
          """,name='agent'))
    response.append(HumanMessage(content="next what should be done?"))
      

    return Command(
        update={'messages':response,'search_result':result["messages"][-1].content},
        goto='supervisor')
    # return result


    
