from agents.sql_with_preprocess.types import AgentState
from agents.sql.main import graph 
from agents.sql.types import AgentState
from langgraph.types import Command
from langchain_core.messages import SystemMessage,AIMessage,HumanMessage,ToolMessage


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



    return Command(
        update={'messages':[AIMessage(content=f"SQL Agent Response: {result['messages'][length:]}"),
                            HumanMessage(content=f"next what should it be done?")],
                
        'sql_query': result['sql_query'],
        'table_name': result['table_name'],
        'docs_schema': result['docs_schema'],
        'relevant_sql_queries': result['relevant_sql_queries'],
        'execution_choice': result['execution_choice']},
        goto='supervisor')

