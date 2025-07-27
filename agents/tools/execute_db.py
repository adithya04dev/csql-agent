import os
import pandas as pd
from google.cloud import bigquery
import base64
import json
import google.auth
from google.oauth2 import service_account
from langchain_core.tools import BaseTool
from langchain_core.callbacks import CallbackManagerForToolRun, AsyncCallbackManagerForToolRun
from pydantic import BaseModel, Field
from typing import Optional, Type
from dotenv import load_dotenv

load_dotenv()

# Load the credentials from the environment variable
credentials_b64 = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
credentials_bytes = base64.b64decode(credentials_b64)
credentials_dict = json.loads(credentials_bytes)
credentials = service_account.Credentials.from_service_account_info(credentials_dict)

class QueryInput(BaseModel):
    """Schema for the query execution input"""
    query: str = Field(description="The SQL query to execute")
    mode: str = Field(default='sql', description="Mode of execution, defaults to 'sql'")

class ExecuteDatabaseTool(BaseTool):
    """Tool for executing BigQuery SQL queries."""
    
    name: str = "execute_db"
    description: str = """Execute a BigQuery SQL query and return the results.
    Useful for running SQL queries against the cricket analytics database."""
    
    args_schema: Type[BaseModel] = QueryInput
    return_direct: bool = False
    
    def _execute_query_sync(self, query: str, mode: str = 'sql'):
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
    
    async def _arun(
        self,
        query: str,
        mode: str = 'sql',
        run_manager: Optional[AsyncCallbackManagerForToolRun] = None
    ) -> str:
        """Execute the SQL query asynchronously."""
        try:
            import asyncio
            loop = asyncio.get_running_loop()
            result = await loop.run_in_executor(None, self._execute_query_sync, query, mode)
            return result
            
        except Exception as e:
            error_msg = f"Error during query execution: {str(e)}"
            print(error_msg)
            return error_msg

    def _run(
        self,
        query: str,
        mode: str = 'sql',
        run_manager: Optional[CallbackManagerForToolRun] = None
    ) -> str:
        """Execute the SQL query synchronously."""
        return self._execute_query_sync(query, mode)

# Create an instance of the tool
tool = ExecuteDatabaseTool()

def execute_query(query: str, mode: str = 'sql'):
    """
    Standalone function to execute BigQuery SQL queries.
    This function can be imported and used by other modules.
    
    Args:
        query (str): The SQL query to execute
        mode (str, optional): Mode of execution, defaults to 'sql'
    
    Returns:
        Result of the query execution
    """
    return tool._execute_query_sync(query, mode)