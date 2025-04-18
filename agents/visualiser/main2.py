from agents.sql_with_preprocess.types1 import AgentState
from langchain_mistralai.chat_models import ChatMistralAI
from typing_extensions import Annotated, TypedDict
from langchain_core.messages import SystemMessage,AIMessage,HumanMessage,ToolMessage
from langgraph.types import Command
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.rate_limiters import InMemoryRateLimiter
from agents.tools.python import python
from langchain.agents import create_tool_calling_agent, AgentExecutor
from langgraph.prebuilt import create_react_agent
from langchain_aws import ChatBedrock
import boto3

from langchain_openai import ChatOpenAI
import uuid 

def get_response(state:AgentState):

    # llm=ChatMistralAI(model='mistral-large')
    # llm=ChatGoogleGenerativeAI(model='gemini-2.0-flash')
    rate_limiter = InMemoryRateLimiter(
    requests_per_second=0.85,  
    check_every_n_seconds=0.1,  
    max_bucket_size=1000  
    )

    # llm = ChatMistralAI(model="mistral-small-latest",rate_limiter=rate_limiter)

    # llm = ChatBedrock(model_id="us.anthropic.claude-3-5-haiku-20241022-v1:0")
    llm=ChatOpenAI(model='o4-mini',reasoning_effort='medium')
    # llm=ChatGoogleGenerativeAI(model='gemini-2.5-pro-preview-03-25')
    # llm=ChatGoogleGenerativeAI(model='gemini-2.0-flash')

    


    matplotlib_messages=SystemMessage(content="""
You are a specialized Visualization Agent for cricket analytics. 
Your task is to create clear, informative visualizations using Python tool( Matplotlib and handle the upload to Cloudinary yourself).

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
   - Return the URL to the user

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
                                      """)

    le=len(state['messages'])
    # print(state['messages'])
    agent = create_react_agent(model=llm, tools=[python],state_modifier=matplotlib_messages)
    # state['messages'].append(HumanMessage(content="Write the code for visualization based on the conversation history"))
    response= agent.invoke({'messages':state['messages']})
    # print(response)
    tool_call_id = str(uuid.uuid4())
    messages=[HumanMessage(content="Visualiser Tool/Agent Called"),
              AIMessage(content=f" Visualiser Agent Last Response : {response['messages'][-1].content.replace('</think>','')}")]

    # messages=response['messages'][le:]
    # messages = []
    # for msg in response['messages'][le:]:
        # if msg.content =='':
        #     msg.content+='tool'

        # if hasattr(msg, 'tool_calls') and len(msg.tool_calls) > 0:
        #     # msg.tool_calls[0]['args']['__arg1'].split()
        #     content = '\n'.join(
        #              line for line in msg.tool_calls[0]['args']['__arg1'].split('\n')
        #              if not line.strip().startswith('#')
        #          ).strip()
        #     msg.content +=f"\n{content}"
        #     print("tool calls appended")
        # messages.append(msg)
    # messages = []
    # for msg in response['messages'][le:]:
    #     if msg.content == '':
    #         # Try to parse arguments if it's a string
    #         try:
    #             import json
    #             arguments = json.loads(msg.additional_kwargs.get('function_call', {}).get('arguments', '{}'))
    #             # Remove commented lines from the extracted Python code
    #             content = '\n'.join(
    #                 line for line in arguments.get('__arg1', '').split('\n') 
    #                 if not line.strip().startswith('#')
    #             ).strip()
    #         except (json.JSONDecodeError, TypeError):
    #             content = ''
    #     else:
    #         content = msg.content
        
    #     if content:  # Only add non-empty messages
    #         messages.append(AIMessage(content=content, additional_kwargs=msg.additional_kwargs))

    # if content =''  AIMessage(content='', additional_kwargs={'function_call': {'name': 'Python', 'arguments': '{"__arg1": "\\nimport 
    # add the __arg1 one into ai message as content
    # if len(messages)>1:
    #     messages[-2].content+=' </think>  '
    #     print("think added")
    # else:
    #    messages.append(AIMessage(content=' </think> '))
    # Create new messages with only content, no other attributes

    messages.append( HumanMessage(content=f"Visualiser Tool/Agent Executed"))
    
    return Command(
        update={'messages':messages},

        goto='supervisor')