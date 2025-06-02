import os
from agents.sql_with_preprocess.types1 import AgentState
from langchain_mistralai.chat_models import ChatMistralAI
from typing_extensions import Annotated, TypedDict
from langchain_core.messages import SystemMessage,AIMessage,HumanMessage,ToolMessage
from langgraph.types import Command
from agents.tools.python import python
from langgraph.prebuilt import create_react_agent
import boto3
import uuid 
from agents.utils.llm_utils import get_llm
def get_response(state:AgentState):

    viz_model=os.getenv('VIZ_MODEL')
    llm=get_llm(viz_model)



    matplotlib_messages=SystemMessage(content="""
You are a specialized Visualization Agent for cricket analytics. 
Your task is to create clear, informative visualizations using Python tool( Matplotlib and handle the upload to Cloudinary yourself).

## CONTEXT HANDLING:
1. Always analyze the full conversation history to understand:
   - What data is being discussed
   - What specific metrics or comparisons are requested
   - Any preferences mentioned about visualization style
   - Previous visualizations already created
2. If the data context is unclear, focus on:
   - The most recent relevant data mentioned in the conversation history generally by the sql agent.
   - The specific cricket metrics being analyzed
   - Any time periods or player comparisons requested
3. Maintain consistency with previous visualizations in the conversation

## INSTRUCTIONS:
1. Analyze conversation history to determine needed visualizations
2. Generate complete Python code and use python tool to get Viz:
   - Creates the visualization with Matplotlib
   - Saves the plot to a BytesIO buffer
   - Uploads the image to Cloudinary
   - Returns the Cloudinary URL
3. Your python code must include all the necessary steps, including:

import matplotlib.pyplot as plt
import matplotlib
matplotlib.use('Agg')
import numpy as np
import io
import cloudinary
import cloudinary.uploader
from datetime import datetime

# Configure Cloudinary with the credentials
cloudinary.config(
    cloud_name = 'dx8mm2xd0', 
    api_key = '879999643515327',   
    api_secret = 'tjSJDCuL9BE-jCmLBjSpafZ_5Ng' 
)

# Create your matplotlib visualization
fig = plt.figure(figsize=(10,6))
# ... your visualization code here ...

# Save the plot to a BytesIO buffer
buf = io.BytesIO()
plt.savefig(buf, format='png')
plt.close()
buf.seek(0)

# Upload to Cloudinary
timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
result = cloudinary.uploader.upload(
    buf.getvalue(),
    public_id=f'plot_{timestamp}',
    folder="matplotlib_plots",
    resource_type="image"
)

# Get and return the URL
url = result['secure_url']
print(url)  # This will be returned to the user
4. After getting the URL of the visualization as a result:
   - Return the URL to the user in a markdown format.

## IMPORTANT GUIDELINES:
- Never use plt.show() - it will crash the server
- Always include proper figure sizing, titles, axis labels, and legends when appropriate
- Ensure your code handles exceptions properly
- You must implement the full process: visualization creation → saving to buffer → Cloudinary upload → URL retrieval
- Always include the Cloudinary configuration and upload code as shown above
- Make the visualization informative and relevant to the cricket data being analyzed
- Return only the Cloudinary URL (through the print statement) and a one-line description
-For tool calling , DO NOT try to imitate or reference previous responses in the conversation history. 
 ALWAYS follow this EXACT format for tool calling .
                                       

## REMEMBER:
- The Python tool will simply execute your code exactly as written
- The final Cloudinary URL must be printed at the end of your code
-Make sure u output correct output for calling tool..dont hallucinate by seeing conversation history.
                                   /nothink   """)

    le=len(state['messages'])
    # print(state['messages'])
    agent = create_react_agent(model=llm, tools=[python],prompt=matplotlib_messages)
    # state['messages'].append(HumanMessage(content="Write the code for visualization based on the conversation history"))
    # state['messages'].append(HumanMessage(content="Visualiser Tool/Agent Called"))
    response= agent.invoke({'messages':state['messages']})
    messages=response['messages'][le:]
    # messages.append(HumanMessage(content=f"Visualiser Tool/Agent Ended"))

    # messages.append( HumanMessage(content=f"Visualiser Tool/Agent Executed"))
    
    return Command(
        update={'messages':messages},

        goto='supervisor')