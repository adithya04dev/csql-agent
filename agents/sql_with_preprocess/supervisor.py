from typing import List, Optional, Literal,TypedDict
from langchain_core.language_models.chat_models import BaseChatModel

from langgraph.graph import StateGraph, MessagesState, START, END
from langgraph.types import Command
from langchain_core.messages import HumanMessage, trim_messages
from agents.sql_with_preprocess.types import AgentState
from langchain_core.messages import HumanMessage,AIMessage,SystemMessage
from typing_extensions import Annotated, TypedDict, Literal
from pydantic import BaseModel, Field

async def make_supervisor_node(llm: BaseChatModel, members: list[str]) -> str:
    options = ["FINISH"] + members

    system_prompt = f"""You are a supervisor orchestrating a multi-turn cricket analytics system with multiple specialized agents.
Your core function is to interpret the user's queries and conversation state, then select the most relevant agent for the NEXT step, knowing control will return to you after each agent completes.

Here are the agents available for routing:
{members}

Your overarching objectives:
1. Act as the central controller: route each step to the appropriate agent, receiving control back after each step
2. Maintain context across multiple turns between agents
3. Route based on both the user query AND the previous agent responses
4. Enable complex workflows requiring multiple agent interactions
5. Only route to FINISH when the entire multi-step query is fully resolved

Below are the agents and their routing guidelines:

1. **search agent**  
   - Route here FIRST when the query requires database lookups of exact values/names/references/enities
   - After search completes, control returns to you to potentially route to sql for data analysis
   - Examples of triggers: specific player names, team names, ground names, country names, competition names,  bat_hand, bowl_style, bowl_kind, line, length, shot

2. **sql agent**  
   - Route here AFTER search has resolved entities
   - Can route back to search if new terms appear in follow-ups
   - Examples: "show stats for that player", "compare these two teams" etc.

3. **chatbot agent**  
   - Handle conversation flow and clarifications
   - Can route to search/sql if user provides additional context
   - Examples: greetings, system questions etc but ready to route elsewhere if cricket queries appear

4. **FINISH**  
   - Route here when ALL steps are complete
   - The query has been fully resolved through potentially multiple agent interactions

Multi-Turn Routing Examples:

1. Complex Query Flow:
   User: "Who was India's best bowler against Australia in 2023?"
   -> search (to identify players) 
   -> returns to supervisor
   -> sql (to analyze statistics)
   -> returns to supervisor
   -> FINISH(shows to user)

2. Interactive Flow:
   User: "Tell me about Virat Kohli's performance"
   -> search (to confirm player reference)
   -> returns to supervisor
   -> sql (to analyze statistics)
   -> returns to supervisor
   -> FINISH(shows to user)
   then
   User follows up above question with : break down by year
   -> sql (query specific stats)
   -> returns to supervisor

   User: "How does this compare to his overall average?"
   -> sql (comparative analysis)
   -> returns to supervisor
   -> FINISH(shows to user)
   
   User: "Thanks, that's all"
   -> FINISH

Return your decision in JSON with the key "next" set to one of the following values: {options}.

Remember:
• You'll regain control after each agent completes
• Route based on both current query and previous agent outputs
• Only route to FINISH when the entire multi-step workflow is complete
• Output must strictly be: next: <agent_or_FINISH>
"""
    class Router(BaseModel):
        """Worker to route to next. If no workers needed, route to FINISH."""
        next: Literal[*options] = Field(description="The next worker to route to")

    async def supervisor_node(state: AgentState) -> Command[Literal[*members, "__end__"]]:
        """An LLM-based router."""
        messages = [
            SystemMessage(content=system_prompt)
        ] + state["messages"]
        response = await llm.with_structured_output(Router).ainvoke(messages)
        goto = response.next
        if goto == "FINISH":
            goto = END

        return Command(goto=goto,update={'messages':HumanMessage(f"Supervisor routed to {goto} agent")})

    return supervisor_node