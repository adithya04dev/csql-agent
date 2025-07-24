from agents.sql_with_preprocess.types1 import AgentState
from agents.tools.execute_db import tool
from langchain_core.messages import SystemMessage,AIMessage,HumanMessage,ToolMessage

async def sql_query_tester(state: AgentState) -> AgentState:

    # if state['execution_choice']==False:
    #     return state
    result = await tool.ainvoke(state['sql_query'])
    
    # Handle result parsing based on tool response format
    if isinstance(result, dict) and 'error' in result:
        # Format: {'sql_result': df, 'error': False}
        state['sql_error'] = result['error']
        state['sql_result'] = result['sql_result']
    elif isinstance(result, str):
        # Format: "Result: \n {df.to_markdown()}\n Error: False" or "Error: ..."
        if result.startswith("Error:"):
            state['sql_error'] = True
            state['sql_result'] = result
        else:
            state['sql_error'] = False
            state['sql_result'] = result
    else:
        # Fallback for unexpected format
        state['sql_error'] = True
        state['sql_result'] = f"Unexpected result format: {str(result)}"
    
    state['attempts'] += 1

    mess = f"Result: \n {state['sql_result']}"
    state['messages'].append(HumanMessage(content=mess))

    return state


# this error
# 400 Table "hdata" must be qualified with a dataset (e.g. dataset.table).; reason: invalid, location: hdata, message: Table "hdata" must be qualified with a dataset (e.g. dataset.table).

# Location: US
# Job ID: 2a674117-99bf-4ebf-88bc-bec2fd3c95f5
