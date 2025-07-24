import os
import pandas as pd
from google.cloud import bigquery
import base64
import json
import google.auth
from google.oauth2 import service_account
from langchain_core.tools import StructuredTool
from dotenv import load_dotenv
import asyncio

load_dotenv()

# Load the credentials from the environment variable
credentials_b64 = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
credentials_bytes = base64.b64decode(credentials_b64)
credentials_dict = json.loads(credentials_bytes)
credentials = service_account.Credentials.from_service_account_info(credentials_dict)

def execute_query_sync(query: str, mode: str = 'sql'):
    """
    Execute a BigQuery SQL query synchronously.
    
    Args:
        query (str): The SQL query to execute
        mode (str, optional): Mode of execution, defaults to 'sql'
    """
    project_id = 'adept-cosine-420005'
    
    try:
        # Create client and execute query synchronously
        client = bigquery.Client(project=project_id, credentials=credentials)
        query_job = client.query(query)
        query_job.result()  # Wait for completion
        df = query_job.to_dataframe()
        
    except Exception as e:
        print("Error occurred in BigQuery execution!")
        result_str = f"Error: {str(e)}\n\nIMPORTANT: This is a SQL execution error. Please review your query syntax, check column names against the schema, and try again. If this is your 4th attempt, summarize the error and stop retrying."
        return result_str
    
    # Return results based on mode
    if mode == 'unique_values':
        return {'sql_result': df, 'error': False}
    else:
        result_str = f"Result: \n {df.head(100).to_markdown(index=False)}\n Error: False"
        return result_str

async def execute_query_async(query: str, mode: str = 'sql'):
    """
    Execute a BigQuery SQL query asynchronously using sync function in executor.
    
    Args:
        query (str): The SQL query to execute
        mode (str, optional): Mode of execution, defaults to 'sql'
    """
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, execute_query_sync, query, mode)

# Create tool with proper sync/async separation
tool = StructuredTool.from_function(
    func=execute_query_sync,  # Sync version for compatibility
    name="execute_db", 
    description="useful to execute the sql query and return back the result",
    coroutine=execute_query_async,  # Async version for LangGraph
)