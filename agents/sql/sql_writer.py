from agents.sql_with_preprocess.types import AgentState
from agents.tools.search_vectordb import tool, SearchPair
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


class Query(BaseModel):
    """ Query for the AI agent to write sql query based on the given conversation """

    query: str = Field(description="The query for which the AI agent needs to write SQL query based on the given conversation")
    table_name: str = Field(description="The table name based on the given conversation")
    change: bool = Field(description="Indicates if the query needs modification")
    execution_choice: bool = Field(description="Indicates if the query should be executed based on user choice")


async def get_query(state:AgentState)->AgentState:
    llm=ChatGoogleGenerativeAI(model='gemini-1.5-flash')

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
    -All tables in database are: ['hdata']
    - Consider full conversation history
    - Focus on cricket statistics context
    """
    
    hum_prompt=f""" Above was the Message conversation history of  AI agent system/state machine.
    The previous state's query paramter was {state['query']} and table_name paramter was {state['table_name']}.
    Now give what should be the query paramter"""
    sys_message=[SystemMessage(content=system_prompt)]
    hum_message=[HumanMessage(content=hum_prompt)]
    result=await structured_llm.ainvoke(sys_message+state['messages']+hum_message)
    state['query'] = result.query
    state['change'] = result.change
    state['execution_choice'] = result.execution_choice
    state['table_name'] = result.table_name

    async with aiofiles.open(rf'C:\Users\adith\Documents\Projects\python-projects\csql-agent\agents\utils\schema_docs\{state['table_name']}_schema.txt','r') as f:
        state['docs_schema']=await f.read()

    return state


async def sql_writer(state:AgentState)->AgentState:
    # write logic for searching relevant queries

    # state=await get_query(state)
    if state['change']:
        # Create a SearchPair object with the required fields
        search_pair = SearchPair(
            search_value=state['query'],
            column_name='sql_queries',
            table_name=state['table_name']
        )
        state['relevant_sql_queries'] = await tool._arun([search_pair])
        append_message=f""" Query Parser Agent:
            Table name :{state['table_name']}
            Table docs and schema: {state['docs_schema']}
            Query: {state['query']}
            Relevant SQL Queries: {state['relevant_sql_queries']}
            """
        state['messages'].append(HumanMessage(content=f"{append_message}",tool_call_id='relevant_sql_queries_tool'))

    llm=ChatGoogleGenerativeAI(model='gemini-2.0-flash-exp')


    # llm=ChatOpenAI(model='Qwen/Qwen2.5-72B-Instruct',temperature=0,base_url="https://api.hyperbolic.xyz/v1",api_key='eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJhZGl0aHlhYmFsYWdvbmkxMUBnbWFpbC5jb20ifQ.3kzGb2_LJoBucaEvozUIc8WGa5ud9W92GtDTQm9lZI4')

    # llm=ChatMistralAI(model='mistral-large-2411')
    sys_prompt=[SystemMessage(content=f"""You are a cricket analytics SQL expert. Generate precise SQL queries for cricket statistics analysis.

DATABASE CONTEXT:
- Schema and documentation: {state['docs_schema']}
- Current table: {state['table_name']}

REQUIREMENTS:
1. Generate valid SQL queries
2. Follow cricket database schema
3. Handle player/match statistics
4. Optimize for performance

RULES:
-understand the context given in the conversation
- Use exact column names
- Include appropriate JOINs
- Handle NULL values
- Follow SQL best practices


""")]

    response=await llm.ainvoke(sys_prompt+state['messages'])
    parsed_query=await parse_sql_query(response.content)
    
    state['messages'].append(AIMessage(content=f"SQL Agent Response : {response.content}"  # Add a default tool_call_id
))
    if parsed_query:
        #add the parsed query to the state message by tool message
        state['messages'].append(AIMessage(content=f"Final SQL query for user query  : {parsed_query}"# Add a default tool_call_id
))
    state['messages'].append(             HumanMessage(content=f"next what should it be done?"))
    return {
        'sql_query':parsed_query
        }
    # return

