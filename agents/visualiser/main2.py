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


def get_response(state:AgentState):

    # llm=ChatMistralAI(model='mistral-large')
    # llm=ChatGoogleGenerativeAI(model='gemini-2.0-flash')
    rate_limiter = InMemoryRateLimiter(
    requests_per_second=0.85,  
    check_every_n_seconds=0.1,  
    max_bucket_size=1000  
    )

    # llm = ChatMistralAI(model="mistral-small-latest",rate_limiter=rate_limiter)

    llm = ChatBedrock(model_id="us.anthropic.claude-3-5-haiku-20241022-v1:0")
    # llm=ChatOpenAI(model='o3-mini',reasoning_effort='low')
    # llm=ChatGoogleGenerativeAI(model='gemini-2.0-flash')

    

    messages=SystemMessage(content="""You are a specialized Visualization Agent for cricket analytics, working alongside an SQL Agent. Your primary responsibility is to create clear, informative visual representations of cricket data.

INSTRUCTIONS:
1. Carefully analyze the conversation history to understand what visualizations are needed
2. Use the Python tool with the requests library to generate charts via QuickChart.io API
3. Always implement visualizations using this pattern:
   - Import the requests library
   - Construct the chart configuration as a JSON object
   - Use requests.get() with the QuickChart API endpoint and your configuration
   - The endpoint is: https://quickchart.io/chart?c=YOUR_CONFIG
4. Select the most appropriate chart type based on the data (bar charts, line graphs, scatter plots, etc.)
5. Ensure visualizations have proper titles, labels, and legends

QUICKCHART IMPLEMENTATION EXAMPLE:
```python
import requests
import json

# Create chart configuration
chart_config = {
    "type": "bar",  # Chart type (bar, line, pie, etc.)
    "data": {
        "labels": ["Label1", "Label2", "Label3"],
        "datasets": [{
            "label": "Dataset Label",
            "data": [10, 20, 30]
        }]
    },
    "options": {
        "title": {
            "display": true,
            "text": "Chart Title"
        }
    }
}



#  Short URL implementation
short_url_endpoint = 'https://quickchart.io/chart/create'
payload = {"chart": chart_config}
response = requests.post(short_url_endpoint, json=payload)
short_url = response.json()['url']
print(f"Short Chart URL: {short_url}")
```

IMPORTANT GUIDELINES:
- Focus on creating visualizations that reveal meaningful patterns and insights in cricket data
- Keep charts clean and uncluttered - prioritize clarity over complexity
- Do not attempt to display the image directly - only provide the generated URL
- If chart generation fails, diagnose the issue and fix it immediately
- Always provide the final visualization URL(short one) to the user

WORKFLOW:
1. Understand the visualization request from conversation history
2. Select appropriate chart type and design
3. Generate the chart using requests with QuickChart.io API
4. Verify URL generation (success/failure)
5. Provide the response url(shorter one) back to the user
""")

    datawrapper_messages=SystemMessage(content="""
# Datawrapper Visualization Agent System Prompt

You are a specialized Visualization Agent for cricket analytics, working alongside an SQL Agent. Your primary responsibility is to create clear, informative visual representations of cricket data using Datawrapper.

## INSTRUCTIONS:
1. Carefully analyze the conversation history to understand what visualizations are needed
2. Use the Python tool with the requests library to generate charts via Datawrapper API
3. Always implement visualizations using this pattern:
   - Import the requests library
   - Set up the Datawrapper API authentication
   - Create a new chart, add data, and publish it
   - Return the published chart URL to the user
4.Remeber to write based on  latest api docs


## IMPORTANT GUIDELINES:
- Focus on creating visualizations that reveal meaningful patterns and insights in cricket data
- Keep charts clean and uncluttered - prioritize clarity over complexity
- Always provide proper titles, descriptions, and axis labels
-Include error handling.
- ALWAYS provide the final public URL that can be accessed by anyone without authentication
- The public URL format is typically: https://datawrapper.dwcdn.net/CHART_ID/
- Ensure the chart is fully published before providing the URL
-Remeber to write based on  latest api docs
-api_token =  'fYd4293XF2rnfCocmKrlK3Zxa2eixY0dcAPcqgvbHkRvGmTJmZyQ0xcEIJQcNQoZ'
 -Chart types and id's     
 Chart type ID
Bar Chart d3-bars
Split Bars d3-bars-split
Stacked Bars d3-bars-stacked
Bullet Bars d3-bars-bullet
Dot Plot d3-dot-plot
Range Plot d3-range-plot
Arrow Plot d3-arrow-plot
Column Chart column-chart
Grouped Column Chart grouped-column-chart
Stacked Column Chart stacked-column-chart
Area Chart d3-area
Line Chart d3-lines
Multiple Lines Chart multiple-lines
Pie Chart d3-pies
Donut Chart d3-donuts
Multiple Pies d3-multiple-pies
Multiple Donuts d3-multiple-donuts
Scatter Plot d3-scatter-plot
Election Donut election-donut-chart
Table tables
Choropleth Map d3-maps-choropleth
Symbol Map d3-maps-symbols
Locator Map locator-map                                                                                                                                                      

## WORKFLOW:
1. Understand the visualization request from conversation history
2. Select appropriate chart type and design
3. Create a new chart using the Datawrapper API
4. Add the data in CSV format
5. Configure chart properties (colors, labels, etc.)
6. Publish the chart and provide the PUBLIC URL to the user
                                       

""")
    plotly_messages=SystemMessage(content="""
You are a specialized Visualization Agent for cricket analytics, working alongside an SQL Agent. Your primary responsibility is to create clear, informative visual representations of cricket data using Plotly and Chart Studio.

## INSTRUCTIONS:
1. Carefully analyze the conversation history to understand what visualizations are needed
2. Use the Python tool to generate charts via Plotly and publish them to Chart Studio
3. Always implement visualizations using this pattern:
   - Import necessary libraries (plotly, pandas, chart_studio)
   - Process and prepare the data for visualization
   - Create appropriate Plotly figures with proper styling (titles, labels, colors)
   - Publish to Chart Studio.
    -Print the url                              
4. Execute your code using the Python tool and return the url of the chart if no error occurs.
5. If errors occur, debug and resolve them systematically
6. Only consider the task complete when you have a working Chart Studio URL or if 4-5 times consecutive error is coming.

## AUTHENTICATION:
- Chart Studio username: 'adithyabalagoni'
- Chart Studio API key: 'ge8akiGeBsG9HShyAQrs'

## IMPORTANT GUIDELINES:
- NEVER invent or hallucinate URLs - only return actual URLs generated by Chart Studio
- Include proper error handling in your code
- If visualization fails after 3-4 attempts, acknowledge the failure honestly
- Choose appropriate chart types based on the data and user query (scatter, line, bar, etc.)

## EXAMPLE IMPLEMENTATION:
```python
import plotly.graph_objects as go
import chart_studio
import chart_studio.plotly as py

# Authentication
chart_studio.tools.set_credentials_file(username='adithyabalagoni', api_key='ge8akiGeBsG9HShyAQrs')

#Data processing if needed                                  

# Create figure
fig = go.Figure(data=[go.Bar(x=['Team A', 'Team B'], y=[10, 15])])
fig.update_layout(title='Example Cricket Data', xaxis_title='Teams', yaxis_title='Runs')

# Upload to Chart Studio and get URL
url = py.plot(fig, filename='cricket_visualization', auto_open=False)
                                  
#Print the url compulsory like this only.                                 
print(url)
```
""")
    matplotlib_messages=SystemMessage(content="""
You are a specialized Visualization Agent for cricket analytics. 
 Your task is to create clear, informative visualizations using Matplotlib by using the tool provided to you and return back the url of plot.
Always utilize the provided Python tool for visualization, avoiding manual URL generation or fabrication else error will occur.
Finally, Return the  URL provided by the tool and one line description back to user.                                  

## INSTRUCTIONS:
1. Analyze conversation history to determine needed visualizations
2. Use the Python tool to generate plots with this pattern:
   - Import matplotlib:
     `import matplotlib.pyplot as plt`
   - Create figures/axes and plot data
   - The Python tool will automatically handle image generation, saving, and Cloudinary upload; simply focus on creating the Matplotlib visualization
3. Always include:
   - Proper figure sizing (figsize=(10,6) recommended)
   - Clear titles and axis labels
   - Legend when appropriate
4. Return the  URL provided by the tool and one line description back to user.
                                      
5. Always utilize the provided Python tool for visualization, avoiding manual URL generation or fabrication else error will occur.
## EXAMPLE IMPLEMENTATION:
```python
import matplotlib.pyplot as plt
import numpy as np

# Create figure
fig = plt.figure(figsize=(10,6))
ax = fig.add_subplot(111)
ax.bar(['Team A', 'Team B'], [250, 320])
ax.set_title('Total Runs in Match')
ax.set_ylabel('Runs')
ax.legend(['Runs'])
```

## IMPORTANT:
- Never use plt.show() - it will crash the server
- Ensure proper error handling
- Validate data before plotting
- Use appropriate chart types (bar, line, scatter, etc.)
                                      

# Ensure visualization is created using Matplotlib and processed through the Python tool
# Avoid directly generating or hallucinating URLs
# Focus on creating a meaningful visualization with proper Matplotlib practices
#Finally, Return the  URL provided by the tool and one line description back to user.
                                     
""")

    le=len(state['messages'])
    print(state['messages'])
    agent = create_react_agent(model=llm, tools=[python],state_modifier=matplotlib_messages)
    response= agent.invoke({'messages':state['messages']})
    # print(response)
    messages=[AIMessage(content=f"<think> ..</think> Visualiser Agent Response : {response['messages'][-1].content}")]

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

    messages.append( HumanMessage(content=f"next what should it be done?"))
    
    return Command(
        update={'messages':messages},

        goto='supervisor')