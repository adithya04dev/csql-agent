from agents.sql_with_preprocess.types import AgentState
from langchain_core.messages import SystemMessage,AIMessage,HumanMessage,ToolMessage


async def router(state: AgentState) -> str:
    # if state["sql_error"] and state['attempts']<3 and state['execution_choice']==False:
        
    #     return "end"
    # else:
    #     state['messages'].append(HumanMessage(content='next what should be done? </think> hello!'))

    #     return "sql_writer"


    if state['execution_choice']==False or state['sql_error']==False or state['attempts']>2:
        return 'end'
    else:
        return 'sql_writer'