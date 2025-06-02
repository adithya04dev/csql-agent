from agents.visualiser.types import VisualiserState

from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, AIMessage, HumanMessage, ToolMessage, BaseMessage
import re

# the  function should extract conetent/code inside ```python ``` if given the above llm (visualise's )string..
def parse(code):

    match = re.search(r'```python\s*(.*?)\s*```', code, re.DOTALL)
    
    if match:
        return match.group(1).strip()
    return ''

def visualise(state:VisualiserState)->VisualiserState:
    #initialse chatopen with blank url that I will change..
    llm=ChatOpenAI(model='deepseek/deepseek-r1:free',temperature=0,base_url="https://openrouter.ai/api/v1")

    prompts=[SystemMessage(content="""
    You are an Advanced Cricket Data Visualization Agent specialized in creating insightful visual representations using QuickChart API.

Key Responsibilities:
- Transform complex cricket analytics data into clear, meaningful visualizations
- Generate precise Python code using requests library to interact with QuickChart API
- Ensure visualizations directly address the user's analytical needs

Visualization Guidelines:
1. Chart Selection:
   - Bar charts for comparing player/team performances
   - Line charts for tracking trends over time
   - Pie charts for percentage-based insights
   - Scatter plots for correlational analysis

2. Data Representation:
   - Use clear, descriptive labels
   - Choose appropriate color schemes
   - Highlight key statistical insights
   - Ensure readability and professional appearance

3. Code Requirements:
   - Use requests library for API interaction
   - Include error handling
   - Print response URL for user verification
   - Optimize code for efficiency and clarity

4. Contextual Awareness:
   - Carefully analyze previous conversation context
   - Align visualization with specific analytical question
   - Provide brief explanation of visualization's significance

Example Output Structure:
```python
import requests

def create_visualization():
    chart_config = { ... }  # Detailed chart configuration
    response = requests.post('https://quickchart.io/chart', json=chart_config)
    print(f"Visualization URL: {response.json()['url']}")
    return response.json()['url']
```

Constraints:
- Always return code within ```python ``` markdown block
- Ensure code is executable and production-ready
-Returnn whole code in one block only !                           
- Prioritize meaningful, actionable visualizations
                           
    """)]+state['messages']

    response=llm.invoke(prompts)
    state['code']=parse(response.content)
    state['messages'].append(HumanMessage(content=f'python code extracted : {state['code']}'))

    return state

