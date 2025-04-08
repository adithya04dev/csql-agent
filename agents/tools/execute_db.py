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
from functools import partial

load_dotenv()

# Load the credentials from the environment variable
credentials_b64 = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
credentials_bytes = base64.b64decode(credentials_b64)
credentials_dict = json.loads(credentials_bytes)
credentials = service_account.Credentials.from_service_account_info(credentials_dict)

def execute_query(query: str,mode:str='sql') -> dict:
    """Synchronous function to execute BigQuery operations"""
    project_id = 'adept-cosine-420005'
    client = bigquery.Client(project=project_id, credentials=credentials)

    try:
        query_job = client.query(query)
        query_job.result()

    except Exception as e:
        print("Error occure man! error!")

        return {'sql_result':str(e),'error':True}
    # print(query_job.to_dataframe().head(30).to_markdown(index=False))
    if mode=='unique_values':
        return {'sql_result':query_job.to_dataframe(),'error':False}
    else:
        return {'sql_result':query_job.to_dataframe().head(30).to_markdown(index=False),'error':False}
    # return {'sql_result':query_job.to_dataframe(),'error':False}


async def arun(query: str) -> dict:
    """Async wrapper around BigQuery operations"""
    # Run the synchronous function in a thread pool to avoid blocking
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, execute_query, query)

tool = StructuredTool.from_function(
    func=execute_query,
    name="SQL Query Executor",
    description="useful to execute the sql query and return back the result",
    coroutine=arun,
)