from agents.sql_with_preprocess.types1 import AgentState
from agents.tools.execute_db import tool
from langchain_core.messages import SystemMessage,AIMessage,HumanMessage,ToolMessage

async def sql_query_tester(state: AgentState) -> AgentState:

    # if state['execution_choice']==False:
    #     return state
    result=await tool.ainvoke(state['sql_query'])
    # print("the result of the execution was result['error']")
    state['sql_error']=result['error']
    state['sql_result']=result['sql_result']
    state['attempts']+=1

    # if state['sql_error']:
    #     mess="Result: \n"
    # else:
    # mess="</think> Result: \n "
    mess=f"Result: \n {state['sql_result']}"
    state['messages'].append(HumanMessage(content=mess))


        

    return state


# this error
# 400 Table "hdata" must be qualified with a dataset (e.g. dataset.table).; reason: invalid, location: hdata, message: Table "hdata" must be qualified with a dataset (e.g. dataset.table).

# Location: US
# Job ID: 2a674117-99bf-4ebf-88bc-bec2fd3c95f5
