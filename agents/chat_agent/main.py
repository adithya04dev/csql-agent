
from agents.sql_with_preprocess.types1 import AgentState
from langchain_mistralai.chat_models import ChatMistralAI
from typing_extensions import Annotated, TypedDict
from langchain_core.messages import SystemMessage,AIMessage,HumanMessage
from langgraph.types import Command
from langchain_google_genai import ChatGoogleGenerativeAI

async def get_response(state:AgentState):

    # llm=ChatMistralAI(model='mistral-large')
    llm=ChatGoogleGenerativeAI(model='gemini-2.0-flash')
    sys_prompt=[SystemMessage(content=f"""
    You are an  chatbot agent part of an AI system that is helping an AI SQL agent for cricket analytics.
    Your expertise is aswering in natural language based on the conversation history.
        """)]

    response=await llm.ainvoke(sys_prompt+ state['messages'])

    return Command(
        update={'messages':[
            AIMessage(content=response.content, name="chat_agent"),
            HumanMessage(content=f"next what should it be done?")
        ]},

        goto='supervisor')