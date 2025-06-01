import os
from langchain_core.messages import SystemMessage
from langchain_openai.chat_models import ChatOpenAI
from dotenv import load_dotenv
from agents.tools.search_vectordb import tool
from langgraph.types import Command
from langchain_core.messages import SystemMessage,AIMessage,HumanMessage,ToolMessage
from agents.sql_with_preprocess.types1 import AgentState
load_dotenv()
from langgraph.prebuilt import create_react_agent

# Add these near your other environment variable loads
import uuid
from langchain_core.rate_limiters import InMemoryRateLimiter
from agents.tools.search_vectordb import tool
from agents.utils.llm_utils import get_llm
async def arun(state: AgentState):


    search_model=os.getenv('SEARCH_MODEL')
    model=get_llm(search_model)


    table_columns = {
    'hdata': [
        'player', 'team', 'dismissal', 'ground', 'country', 'competition', 
        'bat_hand', 'bowl_style((specifies in detail)', 'bowl_kind(broadly classifies like spin or pace)', 'line', 'length', 'shot'
    ],
    'odata_2403': [
        'format', 'ground', 'country', 'team', 'player', 'batsmanHand', 
        'bowlerHand', 'bowlerType', 'dismissalType', 'competition', 'shot_type', 
        'variation', 'length', 'area', 'line', 'foot', 'fielder_action'
    ],
    'ipl_hawkeye': [
        'team', 'player', 'delivery_type(seam,spin etc)', 'ball_type(the variation of the ball)', 'shot_type', 'ball_line', 'ball_length', 
        'wicket_type', 'ground'
    ]
}
    messages=SystemMessage(
        content=f"""You are a Search Agent specialized in cricket analytics, working as part of a multi-agent system.
Your primary role is to help standardize and validate cricket-related terms by matching user inputs to actual database values.

You will be given user conversation based on that u need to interpret and find correct matching values in databse for a query..
You are just an search agent..and need to return text response


Databases and its Schema:
Table: {state['table_name']}
Columns: {', '.join(table_columns[state['table_name']])}
Table hawkeye: 

Your Process:
1. Analyze user queries to identify cricket-related terms that need validation
2. Use the provided search tool to find potential matches in the database
3. After that the search tool returns multiple similar values:
   - Analyze each returned value carefully
   - Consider the context of the user's query
   - Use cricket domain knowledge to select the most appropriate match
4. Return results in a clean JSON format compulsory:
   {{
        "searched_term1": ["actual_database_value1","actual_database_column1"],
          "searched_term2":[ "actual_database_value2","actual_database_column2"]

   }}

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
  response in text/string response of json

Final Output(response text/string response of json): 
```json
{{
    "stev smit": ["Steve Smith","player" ],
    "MCG": ["Melbourne Cricket Ground","ground"],
    "coverdrives": ["cover drive","shot"],
    "fast": ["Fast","bowl_kind"]
}}
```
Remember: 
-Finally return text/string response of json
-Your role is not just to search, but to intelligently interpret and standardize cricket terms for accurate database queries.
-Use the necessary tools to search..dont give on your own previous knowledge.
-you will be given a whole cnversation based on that understad what u need to interpret and search and standardise.
-another point is to rely solely on the information provided by the user; you cannot communicate with them again.
-If no specific valueS is mentioned of a column type dont search..
  it will be handled by sql agent dont worry about it
-You are just an search agent part of an ai multi-agents system..u just need to search and add to conversation and not write sql queries that will be handled by sql agent dont worry about it!   


""")
        
    agent = create_react_agent(model=model, tools=[tool],prompt=messages)
    le=len(state['messages'])

    # state['messages'].append(HumanMessage(content="Search Tool/Agent Called"))
    result = await agent.ainvoke({'messages':state['messages']})
    responses=result['messages'][le:]    
    # responses.append(HumanMessage(content=f"Search Tool/Agent Ended"))
    # Use the same or a new tool_call_id here
      

    return Command(
        update={'messages':responses,'search_result':result["messages"][-1].content},
        goto='supervisor')
    # return result


    
