from typing import List, Optional, Literal,TypedDict
from langchain_core.language_models.chat_models import BaseChatModel

from langgraph.graph import StateGraph, MessagesState, START, END
from langgraph.types import Command
from langchain_core.messages import HumanMessage, trim_messages
from agents.sql_with_preprocess.types1 import AgentState
from langchain_core.messages import HumanMessage,AIMessage,SystemMessage
from typing_extensions import Annotated, TypedDict, Literal
from pydantic import BaseModel, Field
from datetime import datetime

async def make_supervisor_node(llm: BaseChatModel, members: list[str]) -> str:
    options = ["user"] + members

    system_prompt = f"""You are a helpful cricket analytics assistant that can directly answer questions or use specialized tools when needed to analyze cricket data.

You have the following tools available:

1. **search agent**(lookup tool): Looks up specific entities in the cricket database
   - Use for: finding/confirming player names, teams, grounds, countries, bowling styles and many others
   - Perfect for initial lookups when you need to verify entities before analysis
   - IMPORTANT: ALWAYS use this tool FIRST when a user mentions specific cricket entities (players, teams, grounds and many others)

2. **sql agent**(query tool): Runs database queries to analyze cricket statistics
   - Use for: calculating averages, finding top performers, comparing stats
   - IMPORTANT: Only use this AFTER confirming entities with the search agent

3. **visualiser agent**(viz tool): Creates charts and graphs from cricket data
   - Use for: when users specifically ask for visual representation of data
Today's date is  {datetime.now().strftime('%Y-%m-%d')}


   
CRITICAL WORKFLOW INSTRUCTIONS:
- Prioritize using the **search agent** first whenever the user mentions specific, named cricket entities like players, teams, or venues, especially if they haven't been confirmed recently.
- **Also consider the search agent** if the user mentions other terms, categories, or filters (like specific  bowler types, fielding positions, data columns etc.) IF:
    - You are unsure about the exact spelling, validity, or how that term is represented in the **target database table** (`hdata_2403`, `odata_2403`, `ipl_hawkeye`).
    - The term seems like it might refer to a specific value or category within the database that needs clarification before analysis.
- **Example:** If the user asks for "leg spin" bowlers using `ipl_hawkeye`, and you're unsure if "leg spin" is the exact category name used in that table, use the search agent to check available bowler types first.
- NEVER assume the spelling, format, or existence of any specific entity or category name within the target table. Verify first if unsure.
-Think deeply on what values u need to find/lookup ...like think hard motherfucker!
- **Proceed directly to the SQL agent** ONLY IF:
    - All mentioned entities/categories have been recently verified OR
    - The query uses general terms that don't require specific database lookup OR
    - It's a direct follow-up on already verified terms.
    -Already the search agent is called for the given user query.

When routing to the search or sql agents, you must select the appropriate table to query:
Based on the query think about what table would be more sufficient and robust..

- 'hdata_2403': Primary T20 Ball-By-Ball Database (includes IPL matches) containing detailed ball-by-ball information such as line/length, control percentage, shot type, shot angle, and shot zone. Covers T20 matches from 2015 onwards. This is the most recent, reliable, and comprehensive dataset, making it the recommended choice for most queries requiring T20 analysis.
- 'ipl_hawkeye': IPL Hawkeye Data: contains detailed tracking data for IPL matches including BBB data, ball speed, trajectory, deviation, swing, pitch, ball type, shot type coordinates, and spatial information.Covers IPL matches from 2022 onwards. Use this table specifically when analyzing IPL matches that require detailed ball tracking metrics or spatial analysis. While slightly less comprehensive in match coverage than hdata_2403, it provides unique metrics not available elsewhere. Only select this when the query explicitly requires IPL-specific tracking data that cannot be satisfied by hdata_2403.
- 'odata_2403': Mixed Format Ball-By-Ball Data: contains BBB data, shot type, shot area, shot angle, foot movement, granular control for Tests, FC, List A, ODI, T20, and T20I. Covers games mainly from 2019 onwards. This is a slightly older dataset - use it specifically when the user asks for multi-format analysis (Tests, ODIs, etc.) . 




Remember:
- Choose "user" when you want to return control to the user with a complete answer
- When routing to "user", include '</think>' followed by your final response to the user
  * Everything before '</think>' will be hidden in a collapsible section
  * Everything after '</think>' will be displayed immediately to the user
- For new questions, you may need need to search for entities first
- For follow-up questions, you may be able to use existing context without searching again
"""

    class Router(BaseModel):
        """Worker to route to next. If no workers needed, route to user."""
        # think:str=Field(description="Space for structured thinking and reasoning about the user's question. Use this to analyze the query, determine which to  tools are needed, identify entities to look up, plan your approach, and verify that you're following the correct process based on the prompt. ")
        message:str = Field(description="Your message to add to conversation")
        next: Literal[*options] = Field(description="The next worker to route to")
        table_name: Literal['hdata_2403', 'odata_2403', 'ipl_hawkeye'] = Field(description="The table to query")

    async def supervisor_node(state: AgentState) -> Command[Literal[*members, "__end__"]]:
        """An LLM-based router."""
        messages = [
            SystemMessage(content=system_prompt)
        ] + state["messages"]
        response = await llm.with_structured_output(Router).ainvoke(messages)
        state['table_name']=response.table_name
        goto = response.next
        if goto == "user":
            goto = END
        messages=[]
        messages.append(AIMessage(f"Supervisor agent: {response.message.replace('`','')} \n\n Working on  {response.table_name}"))
      #   messages.append(HumanMessage(f"Supervisor agent: routed to {goto} agent"))
        return Command(goto=goto,update={'messages':messages,'table_name':response.table_name,'sequence':f"{state['sequence']} {goto}"})

    return supervisor_node