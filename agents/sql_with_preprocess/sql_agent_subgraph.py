from agents.sql_with_preprocess.types1 import AgentState
from agents.sql.main import graph 
from agents.sql.types import AgentState
from langgraph.types import Command
from langchain_core.messages import SystemMessage,AIMessage,HumanMessage,ToolMessage
import uuid

async def sql_agent_subgraph(state:AgentState)->AgentState:
    
    length=len(state['messages'])
    result=await graph.ainvoke(
    input=state
    )
    # state['messages'].append(result['messages'])
    state['sql_query']=result['sql_query']
    state['table_name']=result['table_name']
    state['docs_schema']=result['docs_schema']
    state['relevant_sql_queries']=result['relevant_sql_queries']
    state['execution_choice']=result['execution_choice']
    #cal


    subgraph_result=''
    for message in result['messages'][length:]:
        subgraph_result+=f'{message.content}\n'
    # subgraph_result = '\n'.join(message.content for message in result['messages'][length:])
    # subgraph_result=subgraph_result.replace('<table>','```')

    tool_call_id = str(uuid.uuid4())


    return Command(
        update={'messages':[HumanMessage(content="SQL Tool/Agent Called"),
                            AIMessage(content=subgraph_result),
                            HumanMessage(content=f"SQL Tool/Agent Executed")],
                
        'sql_query': result['sql_query'],
        'table_name': result['table_name'],
        'docs_schema': result['docs_schema'],
        'relevant_sql_queries': result['relevant_sql_queries'],
        'execution_choice': result['execution_choice']},
        goto='supervisor')

