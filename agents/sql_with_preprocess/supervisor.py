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

    system_prompt = f"""You are a helpful cricket analytics assistant that can directly answer questions
     or use specialized tools when needed to analyze cricket data.


You have the following tools available:

1. **search agent**(lookup tool): Looks up specific entities in the cricket database
   - Use for: finding/confirming player names, teams, grounds, countries, bowling styles and many others
   - Perfect for initial lookups when you need to verify entities before analysis
   - IMPORTANT: ALWAYS use this tool FIRST when a user mentions specific cricket entities (players, teams, grounds and many others)

2. **sql agent**(query tool): Runs database queries to analyze cricket statistics
   - Use for: calculating averages, finding top performers, comparing stats
   - IMPORTANT: Only use this AFTER confirming entities with the search agent

3. **visualiser agent**(viz tool): Creates charts and graphs from cricket data and returns url of chart.
   - Use for: when users specifically ask for visual representation of data
   -After using this tool,return the url of the chart to the user
- Do NOT call the same tool/agent repeatedly more than 2-3  times consecutively and struck in a loop
- Do NOT call the same tool/agent repeatedly more than 2-3  times consecutively and struck in a loop

Today's date is  {datetime.now().strftime('%Y-%m-%d')}


   
CRITICAL WORKFLOW INSTRUCTIONS:
1. **Entity Verification First:** 
   - ALWAYS use the **search agent** first when a user mentions specific cricket entities
   - This includes players, teams, grounds, countries, competitions, and specialized terms..see what all can be searched columns below for a given table
   - Verify entities before analysis to ensure accuracy

2. **When to Use Search Agent:**
   - For initial verification of any named entity
   - When uncertain about exact spelling, format, or existence in the database
   - When dealing with categories/filters (like bowling styles, shot types)...see what all can be searched columns below for a given table
   - When you need to confirm how a term is represented in the target table

3. **When to Skip Search and Use SQL Agent Directly:**
   - All entities have been verified in recent conversation
   - Query uses only general terms not requiring specific lookups
   - Direct follow-up questions using previously verified terms
   - Search agent already called for the current user query

4. **Table Selection Guide:**
   - Choose the most appropriate table based on query asked and the searchable columns that are given below for each table..think while choosing
   - Verify specific columns exist in your chosen table
   - When in doubt about available columns, use search agent first

5. **Example Workflow:**
   - User asks: "What's Virat Kohli's strike rate against leg spinners?"
   - First use search agent on 'hdata' to verify "Virat Kohli" and "leg spin" exist
   - Then use SQL agent to calculate the strike rate

Always verify entities before analysis - accurate data depends on proper identification.

When routing to the search or sql agents, you must select the appropriate table to query:
Based on the query think about what table would be more sufficient and robust..

- 'hdata': Primary T20 Ball-By-Ball Database (includes IPL matches) containing detailed ball-by-ball information such as line/length, control percentage, shot type, shot angle, and shot zone. Covers T20 matches from 2015 onwards. This is the most recent, reliable, and comprehensive dataset, making it the recommended choice for most queries requiring T20 analysis.
    * Searchable columns: player, team, dismissal, ground, country, competition, bat_hand, bowl_style, bowl_kind, line, length, shot.

- 'ipl_hawkeye': IPL Hawkeye Data: contains detailed tracking data for IPL matches including BBB data, ball speed, trajectory, deviation, swing, pitch, ball type, shot type coordinates, and spatial information.Covers IPL matches from 2022 onwards. Use this table specifically when analyzing IPL matches that require detailed ball tracking metrics or spatial analysis. While slightly less comprehensive in match coverage than hdata_2403, it provides unique metrics not available elsewhere. Only select this when the query explicitly requires IPL-specific tracking data that cannot be satisfied by hdata_2403.
    * Searchable columns: team, player, delivery_type, ball_type, shot_type, ball_line, ball_length, wicket_type, ground.

- 'odata_2403': Mixed Format Ball-By-Ball Data: contains BBB data, shot type, shot area, shot angle, foot movement, granular control for Tests, FC, List A, ODI, T20, and T20I. Covers games mainly from 2019 onwards. This is a slightly older dataset - use it specifically when the user asks for multi-format analysis (Tests, ODIs, etc.) . 
        * Searchable columns: player, team, dismissal, ground, country, competition, bat_hand, bowl_style, bowl_kind, line, length, shot.




Remember:
- Choose "user" when you want to return control to the user with a complete answer(like sql result or visualisation link)
- When routing to "user", include '</think>' followed by your final response to the user
  * Everything before '</think>' will be hidden in a collapsible section
  * Everything after '</think>' will be displayed immediately to the user. 
  * Thus, u can include the sql results,visualisation link or a casual message after </think> tag
- For new questions, you may need need to search for entities first
- For follow-up questions, you may be able to use existing context without searching again
- Do NOT call the same agent repeatedly more than 2-3  times consecutively

"""

    class Router(BaseModel):
        """Worker to route to next. If no workers needed, route to user."""
        # think:str=Field(description="Space for structured thinking and reasoning about the user's question. Use this to analyze the query, determine which tools are needed, identify entities/terms to look up, plan your approach, choose the table, and verify workflow steps.")
        
        message:str = Field(description="A short message u want to add to conversation.Include </think> before writing to user. U may include SQL results,visualisation link or a casual message. ")
        next: Literal[*options] = Field(description="The next worker ('search_agent', 'sql_agent', 'visualiser_agent' or 'user'.")
        table_name: Optional[Literal['hdata', 'odata_2403', 'ipl_hawkeye','']] = Field(description="The table to query (MUST be provided if next is 'search_agent' or 'sql_agent').")

    async def supervisor_node(state: AgentState) -> Command[Literal[*members, "__end__"]]:
        """An LLM-based router."""
        messages = [
            SystemMessage(content=system_prompt)
        ] + state["messages"]
        # Trim messages if needed, potentially keeping more history for context
        # trimmed_messages = trim_messages(messages, max_tokens=...)
        response = await llm.with_structured_output(Router).ainvoke(messages)

        # Basic validation
        if response.next in ['search_agent', 'sql_agent'] and not response.table_name:
             # Handle error: LLM failed to provide table name when required
             # Potentially re-prompt or default, here we raise an error for simplicity
             raise ValueError(f"Supervisor Error: Table name missing when routing to {response.next}")

        state['table_name'] = response.table_name
        goto = response.next
        if goto == "user":
            goto = END # LangGraph convention for ending the flow

        ai_message_content = f"Supervisor Action: Routing to {response.next}."
        if response.table_name:
            ai_message_content += f" Target Table: {response.table_name}."
        # Include the LLM's reasoning/message for clarity if needed for debugging/logging
        ai_message_content += f"\n\n Message: {response.message.replace('`','')}"

        new_messages = [AIMessage(content=ai_message_content)]

        return Command(goto=goto, update={'messages': new_messages, 'table_name': response.table_name, 'sequence': f"{state.get('sequence', '')} {goto}"})


    return supervisor_node