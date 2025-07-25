from agents.sql_with_preprocess.types1 import AgentState
from agents.tools.search_vectordb import tool, SearchPair
from agents.utils.llm_utils import get_llm
from langchain_mistralai.chat_models import ChatMistralAI
from typing_extensions import Annotated, TypedDict
from langchain_core.messages import SystemMessage,AIMessage,HumanMessage,ToolMessage
from langgraph.types import Command

from agents.tools.parse import parse_sql_query
import uuid
import aiofiles
from langchain_openai.chat_models import ChatOpenAI
from langchain_google_genai import ChatGoogleGenerativeAI
from typing import Optional
from pydantic import BaseModel, Field
from dotenv import load_dotenv
import os
load_dotenv()
sql_model=os.getenv('SQL_MODEL')
class Query(BaseModel):
    """ Query for the AI agent to write sql query based on the given conversation """

    query: str = Field(description="The query for which the AI agent needs to write SQL query based on the given conversation")
    table_name: str = Field(description="The table name based on the given conversation")
    change: bool = Field(description="Indicates if the query needs modification")
    execution_choice: bool = Field(description="Indicates whether the query should be executed. Defaults to `True` unless the user explicitly states not to execute it in the conversation.")

async def get_query(state:AgentState)->AgentState:
    llm=ChatGoogleGenerativeAI(model='gemini-2.0-flash')

    structured_llm = llm.with_structured_output(Query)
    system_prompt = f"""You are an AI assistant analyzing cricket analytics queries. Your role is to extract query parameters from conversations.
    
    KEY RESPONSIBILITIES:
    1. Analyze conversation history
    2. Determine if previous query needs changes
    3. Extract table names from context
    4. Set execution choice

    PARAMETERS TO RETURN:
    - query: The analyzed query text
    - table_name: Target cricket database table
    - change: Boolean (true if query needs modification)
    - execution_choice: Boolean (true if query should execute)(based on the user choice given in conversation)

    CONTEXT RULES:
    - Previous state query: {state['query']}
    - Previous table: {state['table_name']}

    -All tables in database are: ['hdata_0510']
    - Consider full conversation history
    - Focus on cricket statistics context
    """
    
    hum_prompt=f""" Above was the Message conversation history of  AI agent system/state machine.
    The previous state's query paramter was {state['query']} and table_name paramter was {state['table_name']}.
    Now give what should be the query,table_name,change,execution_choice(Defaults to `True` unless the user explicitly says) paramter"""
    sys_message=[SystemMessage(content=system_prompt)]
    hum_message=[HumanMessage(content=hum_prompt)]
    result=await structured_llm.ainvoke(sys_message+state['messages']+hum_message)
    state['query'] = result.query
    state['change'] = result.change
    state['execution_choice'] = result.execution_choice
    state['table_name'] = result.table_name

    async with aiofiles.open(f"./agents/utils/schema_docs/{state['table_name']}_schema.txt",'r') as f:
        state['docs_schema']=await f.read()

    return state


async def sql_writer(state:AgentState)->AgentState:
    # write logic for searching relevant queries

    # state=await get_query(state)
    # context=''
    # if state['change']:
    #     # Create a SearchPair object with the required fields
    #     search_pair = SearchPair(
    #         search_value=state['query'],
    #         column_name='sql_queries',
    #         table_name='hdata'   #state['table_name']
    #     )
    #     state['relevant_sql_queries'] = await tool._arun([search_pair])
    #     append_message=f""" 

    #         Some Relevant SQL Queries: {state['relevant_sql_queries']}
    #         """
    #     context=HumanMessage(content=append_message,tool_call_id='relevant_sql_queries_tool')


    async with aiofiles.open(f"./agents/utils/schema_docs/{state['table_name']}_schema.txt",'r') as f:
        state['docs_schema']=await f.read()
    sys_prompt=[SystemMessage(content=f"""You are a SQL agent for cricket analytics that works with search and visualizer agents.

**CONTEXT: I have a ball by ball dataset of cricket matches. I want you to write sql queries to analyze the data.**
**DATABASE INFO of Bigquery:**
- Dataset Name : 'bbbdata'
- Table: {state['table_name']}
- Schema: {state['docs_schema']}

**YOUR TASK:**
- Read the conversation context
- Write precise BigQuery SQL based on user requests
- Use exact schema column names
- Calculate cricket metrics accurately

**KEY METRICS TO INCLUDE:**

For Batting: Core: Runs, balls faced, dismissals | Standard: Average, strike rate (runs/balls*100), control % | Additional: Boundary %, dot ball %
For Bowling: Core: Overs/balls, runs conceded, wickets | Standard: Average, economy, strike rate | Additional: Dot ball %, boundary % conceded

**BEST PRACTICES:**
- Use CTEs for complex calculations
- Filter appropriately (valid deliveries, match types)
- Handle edge cases (division by zero, nulls)
- Structure queries logically
- Use the search agent results as it has verified entities

Return ONLY SQL in markdown format:
```sql
YOUR_QUERY_HERE
```
""")]+state['messages']
    # if context!='':
    #     sys_prompt.append(context)
    # llm=ChatOpenAI(model='o3-mini',reasoning_effort='high')
    llm=get_llm(sql_model)
    state['messages'].append(HumanMessage(content='Write Query by understanding the context.'))
    response=await llm.ainvoke(sys_prompt)
    parsed_query=await parse_sql_query(response.content)
    state['sql_query']=parsed_query
    # state['messages'].append(AIMessage(content=f"SQL Agent Response : {response.content}"  ))
    if parsed_query:
        #add the parsed query to the state message by tool message
        state['messages'].append(AIMessage(content=f"SQL Query :\n {parsed_query.replace('`', '')}"# Add a default tool_call_id
        ))
    else:
        state['messages'].append(AIMessage(content='Couldnt parse/extract the sql query. Try again by returning sql query in markdown format!.'))
    
    return state
    # return

