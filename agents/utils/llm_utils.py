import os
from langchain.chat_models import init_chat_model
from dotenv import load_dotenv

load_dotenv()

def get_llm(model_name):
    if model_name.startswith('gemini'):
        llm=init_chat_model(model=model_name,model_provider='google_genai',api_key=os.getenv('GOOGLE_API_KEY'))
    else:
        llm=init_chat_model(model=model_name)
    return llm 