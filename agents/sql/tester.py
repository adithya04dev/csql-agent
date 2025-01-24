from agents.sql_with_preprocess.types import AgentState
from agents.tools.execute_db import tool
from langchain_core.messages import SystemMessage,AIMessage,HumanMessage,ToolMessage

async def sql_query_tester(state: AgentState) -> AgentState:

    if state['execution_choice']==False:
        return state

    result=await tool.ainvoke(state['sql_query'])

    state['error']=result['error']
    state['sql_result']=result['sql_result']
    state['attempts']+=1
    mess=f"""SQL Database Executor:

    Executing query: {state['sql_query']}

    Result: {str(state['sql_result'])}

    Error: {str(state['error'])} (True if error occured else False)


    """
    state['messages'].append(ToolMessage(content=mess))
        

    return AgentState

