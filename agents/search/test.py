import sys
import os
import asyncio

# Add the project root to the Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

# Now import using the absolute paths
from agents.sql_with_preprocess.types import AgentState
from langchain_core.messages import HumanMessage
from agents.search.main import arun

async def test_query(query: str) :
    """Test a single query and return timing + results"""
    
    state = AgentState(
        messages=[HumanMessage(content=query)],
        query="",
        execution_choice=False,
        sql_query="",
        sql_result="",
        relevant_sql_queries="",
        sql_error=False,
        referenced_values_in_table="",
        table_name="",
        docs_schema="",
        change="",
        attempts=0,
    )
    
    try:
        result = await arun(state)
        response = result['messages'][-1].content
    except Exception as e:
        response = f"Error: {str(e)}"
    return response

if __name__=='__main__':
    # Create an event loop and run the async function
    response = asyncio.run(test_query('rahul tripathi ipl stats'))
    print(response)
        
    # end_time = time()
    
    # return {
    #     "query": query,
    #     "response": response,
    #     "time_taken": round(end_time - start_time, 2)
    # }
