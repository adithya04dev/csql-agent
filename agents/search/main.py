import os
from langchain_core.messages import SystemMessage
# from langchain_openai.chat_models import ChatOpenAI
from dotenv import load_dotenv
from agents.tools.search_vectordb import tool
from langgraph.types import Command
from langchain_core.messages import SystemMessage
from agents.sql_with_preprocess.types1 import AgentState
load_dotenv()
from langgraph.prebuilt import create_react_agent

# Add these near your other environment variable loads
import uuid
# from langchain_core.rate_limiters import InMemoryRateLimiter
from agents.tools.search_vectordb import tool
from agents.utils.llm_utils import get_llm
async def arun(state: AgentState):


    search_model=os.getenv('SEARCH_MODEL')
    model=get_llm(search_model)


    table_columns = {
    'cricinfo_bbb': [
        'player', 'team', 'dismissal', 'ground', 'country', 'competition', 
        'bat_hand', 'bowl_style((specifies in detail)', 'bowl_kind(broadly classifies like spin or pace)', 'line', 'length', 'shot'
    ],

    'aucb_bbb': [
        'ground', 'competition', 'team', 'player', 'country', 'dismissalType', 'fieldingPosition',
        'noBallReasonId', 'battingShotTypeId', 'battingFeetId', 'battingHandId', 'bowlingTypeId(spin,pace,offspin etc)',
        'bowlingFromId', 'bowlingDetailId(variations of bowling like slower ball etc)', 'appealDismissalTypeId', 'referralOutcomeId'
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
-If no specific values is mentioned of a column type and just said to be grouped or grouped by we do not need to search.
  it will be handled by sql agent dont worry about it
-When queries ask for grouping using words like "by", "per" (e.g., "by year", "by length", "per team"), no need to search for those column values as they'll be used in GROUP BY clauses.

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


Some frequently used queries and how you should proceed with them:
-like some of queries include player names..try to search for them..
-some queries may include tournament names/competitions..try to search for them..
-some queries may include ground names..try to search for them..
-some may include country or team names(even of well known tournaments )
-some may include bowl style,kind,variation or line length,shot type..
but in some scenarios its not necessary to search for them..
-like something about over/under runs or wickets,batting position as its just numbers ,seacrhing for those is waste of time.
-or if queries asked about group by another column dont search because we can write group by and we dont write anything in where clause..so thats why no need..
so only search for those that needs to be in where clause..






Remember: 
-Finally return text/string response of json
-Your role is not just to search, but to intelligently interpret and standardize cricket terms for accurate database queries.
-Use the necessary tools to search..dont give on your own previous knowledge.
-you will be given a whole cnversation based on that understad what u need to interpret and search and standardise.
  -If no specific valueS is mentioned of a column type dont search..
-You are just an search agent part of an ai multi-agents system..u just need to search and add to conversation and not write sql queries that will be handled by sql agent dont worry about it!   
-Handle database inconsistencies: If you find multiple similar variations of the same entity (like "Varun Chakaravarthy" vs "Varun Chakravarthy" or "Bangalore" vs "Bengaluru"), include both variations in your response to ensure comprehensive matching.


-another point is to rely solely on the information provided by the user; you cannot communicate with them again.

-Focus on your search job only - don't try to mimic what other agents do or say. Do your search work and let other agents handle their own tasks.

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


    
