import os
from langchain_core.messages import SystemMessage
from dotenv import load_dotenv
from agents.tools.execute_db import tool as execute_tool
from langgraph.types import Command
from langchain_core.messages import SystemMessage, AIMessage, HumanMessage
from agents.sql_with_preprocess.types1 import AgentState
load_dotenv()
from langgraph.prebuilt import create_react_agent
import aiofiles
from agents.utils.llm_utils import get_llm

async def arun(state: AgentState):
    # Get the appropriate model from environment variables
    sql_model = os.getenv('SQL_MODEL')
    model = get_llm(sql_model)

    # Load the database schema for the current table
    try:
        async with aiofiles.open(f"./agents/utils/schema_docs/{state['table_name']}_schema.txt", 'r') as f:
            state['docs_schema'] = await f.read()
    except Exception as e:
        # Fallback for when schema file doesn't exist
        state['docs_schema'] = "Schema file not found. Please ensure table name is correct."
        print(f"Error loading schema: {e}")

    # Create the system message for the SQL agent
    messages = SystemMessage(
        content=f"""
You are a SQL Agent for cricket analytics. Answer/respond to user questions about cricket data based on the conversation history as you have a database(Bigquery) of cricket data that you can query using tool.

**DATABASE INFO:**
- Dataset: 'bbbdata_csql'
- Table: {state['table_name']}
- Ball-by-ball cricket data

**BEFORE WRITING SQL:**
1. Describe your approach in 1-2 sentences
2. Identify key columns needed from schema
3. Explain any filtering/grouping logic

**YOUR WORKFLOW:**
1. Plan your approach (describe before coding)
2. Write BigQuery SQL using exact schema column names
3. Execute with SQL Query Executor tool
4. MAX 3 retry attempts if errors occur
5. If still failing after 2 attempts, return error summary

**BIGQUERY SYNTAX NOTES:**
- Use `bbbdata_csql.{state['table_name']}` format
- Window functions: ROW_NUMBER() OVER (PARTITION BY col ORDER BY col)
- Exclude invalid deliveries: WHERE wide = 0 AND noball = 0
- Use backticks around `over` column: `over`

**VALIDATE RESULTS:**
- Check if result size makes sense for the question
- For "first N" queries, verify row counts per player
- Ensure logic matches user intent

**RESPONSE FORMAT:**
- Success: "Results obtained: [one-line query description]"
- Error after 3 attempts: "Query failed: [brief error summary]"
- Let tool results display automatically - don't reformat them

**SCHEMA:**
{state['docs_schema'].split('docs and some sample queries')[0].strip()}
"""
    )

    # Create a ReAct agent with the SQL execution tool
    agent = create_react_agent(model=model, tools=[execute_tool],prompt=messages)
    
    # Store the starting message index to track new messages
    le = len(state['messages'])
    
    # Invoke the agent with the current conversation
    # state['messages'].append(HumanMessage(content="SQL Agent Called"))
    result = await agent.ainvoke({'messages': state['messages']})
    
    # Extract just the new messages added by this agent
    responses = result['messages'][le:]
    # responses.append(HumanMessage(content=f"SQL Agent Ended"))
    #hey iterate through messagesaand if any assistant message has 
    # Return command to update state and go to supervisor
    return Command(
        update={
            'messages': responses
        },
        goto='supervisor') 