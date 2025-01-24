
from agents.sql_with_preprocess.main import graph

async def runworkflow(query: str): 
    #run the 
    result = await graph.ainvoke(query)
    return result