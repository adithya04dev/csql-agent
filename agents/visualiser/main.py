from langgraph.graph import StateGraph, END
from agents.visualiser.types import VisualiserState
from agents.visualiser.visualise import visualise
from agents.visualiser.code_interpreter import execute_code
from agents.visualiser.router import router
from langchain.schema import SystemMessage, HumanMessage
from agents.sql_with_preprocess.types1 import AgentState

def create_visualiser_graph(messages):
    """
    Create a graph workflow for the visualiser agent
    
    Args:
        messages (list): List of messages (human, ai, system) from langchain
    
    Returns:
        Compiled graph ready to be invoked
    """
    workflow = StateGraph(VisualiserState)
    
    # Add nodes
    workflow.add_node("visualise", visualise)
    workflow.add_node("code_interpreter", execute_code)
    
    # Add edges
    workflow.set_entry_point("visualise")
    workflow.add_edge("visualise", "code_interpreter")
    workflow.add_conditional_edges("code_interpreter", router)
 
    
    # Compile the graph
    graph = workflow.compile()
    
    # Initialize state
    initial_state = {
        "messages": messages,
        "code": None,
        "code_error": "",
        "attempts": 0
    }
    
    return graph, initial_state

def run_visualiser(state:AgentState)->AgentState:
    """
    Run the visualiser workflow with given messages
    
    Args:
        messages (list): List of messages (human, ai, system) from langchain
    
    Returns:
        Final state of the graph after execution
    """
    graph, initial_state = create_visualiser_graph(state['messages'])
    final_state = graph.invoke(initial_state)
    state['messages'].append(HumanMessage(content='<think>  '))
    state['messages']=final_state['messages']
    return state

# Example usage
if __name__ == "__main__":
    # Example messages - replace with actual messages from your workflow
    example_messages = [
        SystemMessage(content="Visualize cricket player performance"),
        HumanMessage(content="Create a bar chart of batting averages")
    ]
    result = run_visualiser(example_messages)
    print("Visualization Result:", result)


# graph like other graphs given in context..with visualise node, tester noderouter node,

# visualise->tester->router back to visualiser or end!

# i will invoke the graph with a list of human,ai,system message of langchain 