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
        content=f"""You are a SQL Agent specialized in cricket analytics, working as part of a multi-agent system.
Your primary role is to generate precise BigQuery SQL queries based on user requests and execute them.

**DATABASE INFO:**
- Dataset Name: 'bbbdata'
- Table: {state['table_name']}
- Schema: {state['docs_schema']}

**YOUR TASK:**
- Analyze the user conversation to understand the query intent
- Generate precise BigQuery SQL that answers the user's question
- Use exact schema column names from the provided schema
- Test your query with the SQL Query Executor tool
-Finally if  u get result return "results were obtained" and if any error(even after multiple attempts) write a small description of error.

**KEY CRICKET METRICS TO INCLUDE:**
For Batting: Runs, balls faced, dismissals, Average, strike rate, boundary %, dot ball %
For Bowling: Overs/balls, runs conceded, wickets, Average, economy, strike rate

**SQL WRITING BEST PRACTICES:**
- Use CTEs for complex calculations
- Filter appropriately (valid deliveries, match types)
- Handle division by zero with NULLIF()
- Always qualify tables with 'bbbdata.' prefix
- Structure queries logically with comments

**YOUR WORKFLOW:**
1. Analyze the conversation request
2. Draft an SQL query based on the schema
3. Execute it with the SQL Query Executor tool
4. If errors occur, fix and retest

IMPORTANT: The SQL Query Executor tool already includes the results in its output. DO NOT repeat or reformat the results yourself. Simply let the tool output appear in the conversation.
"""
    )

    # Create a ReAct agent with the SQL execution tool
    agent = create_react_agent(model=model, tools=[execute_tool], state_modifier=messages)
    
    # Store the starting message index to track new messages
    le = len(state['messages'])
    
    # Invoke the agent with the current conversation
    # state['messages'].append(HumanMessage(content="SQL Agent Called"))
    result = await agent.ainvoke({'messages': state['messages']})
    
    # Extract just the new messages added by this agent
    responses = result['messages'][le:]
    # responses.append(HumanMessage(content=f"SQL Agent Ended"))
    # Return command to update state and go to supervisor
    return Command(
        update={
            'messages': responses
        },
        goto='supervisor') 