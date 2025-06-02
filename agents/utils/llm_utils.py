import os
from langchain.chat_models import init_chat_model
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_google_genai import ChatGoogleGenerativeAI
# from langchain_anthropic import ChatAnthropic

load_dotenv()

def get_llm(model_name):
    if model_name.startswith('gemini'):
        # llm=init_chat_model(model=model_name,model_provider='google_genai',api_key=os.getenv('GOOGLE_API_KEY'))
        llm=ChatGoogleGenerativeAI(model=model_name,api_key=os.getenv('GOOGLE_API_KEY'))
    elif model_name.startswith('openrouter'):
        # llm=init_chat_model(model=f"openai:{model_name.split(':')[1]}",api_key=os.getenv('OPENROUTER_API_KEY'),base_url='https://openrouter.ai/api/v1')
        llm=ChatOpenAI(model=model_name.split(':', 1)[1],api_key=os.getenv('OPENROUTER_API_KEY'),base_url='https://openrouter.ai/api/v1')
        
    else:
        llm=init_chat_model(model=model_name)
    return llm 