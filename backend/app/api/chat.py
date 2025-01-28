import json
import uuid
from typing import AsyncGenerator, List, Optional
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from agents.sql_with_preprocess.main import create_graph
from langchain_core.messages import HumanMessage
from agents.sql_with_preprocess.types import AgentState

router = APIRouter()

# Match OpenAI's chat completion request format
class ChatMessage(BaseModel):
    role: str = Field(..., description="The role of the message sender (system/user/assistant)")
    content: str = Field(..., description="The content of the message")
    name: Optional[str] = Field(None, description="Optional name for the message sender")

class ChatRequest(BaseModel):
    model: str = Field(..., description="Model to use for completion")
    messages: List[ChatMessage] = Field(..., description="List of messages in the conversation")
    temperature: Optional[float] = Field(0.7, description="Sampling temperature")
    stream: Optional[bool] = Field(False, description="Whether to stream the response")
    max_tokens: Optional[int] = Field(None, description="Maximum tokens to generate")

async def stream_response(app, initial_state) -> AsyncGenerator[str, None]:
    response_id = f"chatcmpl-{uuid.uuid4()}"
    created = int(__import__('time').time())  # Match OpenAI's timestamp format

    # Send the initial response format
    initial_chunk = {
        "id": response_id,
        "object": "chat.completion.chunk",
        "created": created,
        "model": "your-model-name",
        "choices": [{
            "index": 0,
            "delta": {"role": "assistant"},
            "finish_reason": None
        }]
    }
    yield f"data: {json.dumps(initial_chunk)}\n\n"

    # async for event in app.astream_events(initial_state, version='v1'):
    async for val,event in app.astream(initial_state, stream_mode=["updates"]):

        content = str(list(event.values())[0]['messages'])+'\n\n'
        
        chunk = {
            "id": response_id,
            "object": "chat.completion.chunk",
            "created": created,
            "model": "your-model-name",
            "choices": [{
                "index": 0,
                "delta": {"content": content},
                "finish_reason": None
            }]
        }
        yield f"data: {json.dumps(chunk)}\n\n"

    # Send the final chunk with finish_reason
    final_chunk = {
        "id": response_id,
        "object": "chat.completion.chunk",
        "created": created,
        "model": "your-model-name",
        "choices": [{
            "index": 0,
            "delta": {},
            "finish_reason": "stop"
        }]
    }
    yield f"data: {json.dumps(final_chunk)}\n\n"
    yield "data: [DONE]\n\n"

@router.post("/v1/chat/completions")  # Match OpenAI's endpoint path
async def chat_endpoint(request: ChatRequest):
    try:
        app = await create_graph()

        # Get the last user message from the conversation
        user_message = next(
            (msg.content for msg in reversed(request.messages) if msg.role == "user"),
            None
        )
        
        if not user_message:
            raise HTTPException(status_code=400, detail="No user message found in the conversation")

        initial_state = AgentState(
            messages=[HumanMessage(content=user_message)],
            query='',
            execution_choice=False,
            sql_query=None,
            sql_result="",
            relevant_sql_queries="",
            sql_error=False,
            referenced_values_in_table="",
            table_name=None,
            docs_schema="",
            change="",
            attempts=0,
            sequence=''
        )

        # Handle both streaming and non-streaming responses
        if request.stream:
            return StreamingResponse(
                stream_response(app, initial_state),
                media_type="text/event-stream"
            )
        else:
            # For non-streaming responses, collect the entire response
            response_text = ""
            # async for event in app.astream_events(initial_state, version='v1'):
            # async for event in app.astream(initial_state, stream_mode=['updates']):
            #     response_text += str(event)
            async for values,event in app.astream(initial_state, stream_mode=["updates"]):
                
                response_text+= str(list(event.values())[0]['messages']) +'\n\n'
                # response_text+= str(event+'\n')


            return {
                "id": f"chatcmpl-{uuid.uuid4()}",
                "object": "chat.completion",
                "created": int(__import__('time').time()),
                "model": "your-model-name",
                "choices": [{
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": response_text
                    },
                    "finish_reason": "stop"
                }],
                "usage": {
                    "prompt_tokens": 0,  # You may want to implement token counting
                    "completion_tokens": 0,
                    "total_tokens": 0
                }
            }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# # backend/app/api/chat.py




# async def stream_response(app, initial_state) -> AsyncGenerator[str, None]:
#     async for event in app.astream_events(initial_state, version='v1'):

#         yield str(event)


# @router.post("/chat", response_model=ChatResponse)
# async def chat_endpoint(request: ChatRequest):
#     try:
#         app = await create_graph()
#         initial_state = AgentState(
#             messages=[HumanMessage(content=request.message)],
#             query='',
#             execution_choice=False,
#             sql_query=None,
#             sql_result="",
#             relevant_sql_queries="",
#             sql_error=False,
#             referenced_values_in_table="",
#             table_name=None,
#             docs_schema="",
#             change="",
#             attempts=0,
#             sequence=''
#         )
#         return StreamingResponse(stream_response(app, initial_state), media_type="text/plain")
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=str(e))