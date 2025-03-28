
from agents.visualiser.types import VisualiserState
from langgraph.graph import END
from langchain_core.messages import HumanMessage

def router(state:VisualiserState)->VisualiserState :
    
    if state["code_error"]=='' or state['attempts']>3:
        return END
    else:
        state['messages'].append(HumanMessage(content=f"python error :{ state['code_error']}\n Try fixing it !"))
        state['vattempts']+=1
        return "code_interpreter"
    