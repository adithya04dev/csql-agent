from agents.sql_with_preprocess.types import AgentState


async def router(state: AgentState) -> str:
    if state["sql_error"] and state['attempts']<3 and state['execution']==False:
        
        return "end"
    else:
        return "sql_writer"
