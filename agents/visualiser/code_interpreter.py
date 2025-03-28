
from langchain.tools import BaseTool, StructuredTool, tool
from langchain_experimental.utilities import PythonREPL
from langchain_core.tools import Tool
from agents.visualiser.types import VisualiserState
from langchain_core.messages import HumanMessage



python_repl = PythonREPL()

def execute_code(state:VisualiserState)->VisualiserState:
    """Execute Python code using a REPL environment.
    
    Args:
        code (str): The Python code to execute
        
    Returns:
        str: The output of the executed code
    """
    try:
        res=python_repl.run(state['code'])
        state['result']=res
        state['messages'].append(HumanMessage(content=f"Code Execution Result: {res}"))
        state['code_error']=''
    except Exception as e:
        state['code_error']=str(e)
    return state
