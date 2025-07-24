import json
import uuid
from typing import AsyncGenerator, List, Optional,Dict
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field,validator
from agents.sql_with_preprocess.main import create_graph
from langchain_core.messages import HumanMessage
from agents.sql_with_preprocess.types1 import AgentState
from langchain_core.messages import AnyMessage
from langchain_core.messages import HumanMessage,AIMessage,SystemMessage
from langchain_core.messages import AnyMessage

router = APIRouter()

# Match OpenAI's chat completion request format
class ChatMessage(BaseModel):
    role: str = Field(..., description="The role of the message sender (system/user/assistant)")
    content: str = Field(..., description="The content of the message")
    # reasoning:str =Field(None,description="The reasoning part of message")
    # name: str = Field(None, description="Optional name for the message sender")


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
        "model": "sql-agent",
        "choices": [{
            "index": 0,
            "delta": {"role": "assistant"},
            "finish_reason": None
        }]
    }
    yield f"data: {json.dumps(initial_chunk)}\n\n"

    # async for event in app.astream_events(initial_state, version='v1'):
    first=True
    async for chunk in app.astream(initial_state, 
                                   subgraphs=True,
                                   stream_mode=["updates"]):
        
        val,upd,event=chunk

        # print(" the chunk is :",chunk)

        if 'search' in event or 'sql' in event or 'visualiser' in event: 
            continue


        if first:
            content='<think>'
            first=False
        else:
            content=''
        response =list(event.values())[0]['messages']
        if isinstance(response, list):

            for msg in response:
                if msg.name!='agent':
                    if isinstance(msg.content, list):
                        # Handle the case when content is a list
                        content += '\n\n'.join(msg.content) + '\n\n'
                    else:
                        content += msg.content + '\n\n'
        else:
            if response.name!='agent':
                if isinstance(response.content, list):
                    # Handle the case when content is a list
                    content += '\n\n'.join(response.content) + '\n\n'
                else:
                    content += response.content + '\n\n'
        # content+= str(list(event.values())[0]['messages'])+'\n\n'

        chunk = {
            "id": response_id,
            "object": "chat.completion.chunk",
            "created": created,
            "model": "sql-agent",
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
        "model": "sql-agent",
        "choices": [{
            "index": 0,
            "delta": {},
            "finish_reason": "stop"
        }]
    }
    yield f"data: {json.dumps(final_chunk)}\n\n"
    # yield "data: [DONE]\n\n"

@router.post("/v1/chat/completions")  # Match OpenAI's endpoint path
async def chat_endpoint(request: ChatRequest):
    try:
        app = await create_graph()
        # print("messages are: ")
        # print(request.messages)
        # Get the last user message from the conversation
        # user_message = next(
        #     (msg.content for msg in reversed(request.messages) if msg.role == "user"),
        #     None
        # )
        messages=[]
        for message in request.messages:
            if message.role=='assistant' :
                messages.append(AIMessage(content=message.content))
            elif message.role=='user':
                messages.append(HumanMessage(content=message.content))


        
        if not messages:
            raise HTTPException(status_code=400, detail="No user message found in the conversation")

        initial_state = AgentState(
            messages=messages,
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
            print("streaming now")
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
                if isinstance(list(event.values())[0]['messages'], list):
                    for msg in list(event.values())[0]['messages']:
                        if isinstance(msg.content, list):
                            # Handle the case when content is a list
                            response_text += '\n\n'.join(msg.content) + '\n\n'
                        else:
                            response_text += str(msg.content) + '\n\n'
                else:
                    if isinstance(list(event.values())[0]['messages'].content, list):
                        # Handle the case when content is a list
                        response_text += '\n\n'.join(list(event.values())[0]['messages'].content) + '\n\n'
                    else:
                        response_text += str(list(event.values())[0]['messages'].content) + '\n\n'

            return {
                "id": f"chatcmpl-{uuid.uuid4()}",
                "object": "chat.completion",
                "created": int(__import__('time').time()),
                "model": "sql-agent",
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
        print(str(e))
        raise HTTPException(status_code=500, detail=str(e))





# import json
# import uuid
# import re
# from typing import AsyncGenerator, List, Optional
# from fastapi import APIRouter, HTTPException
# from fastapi.responses import StreamingResponse
# from pydantic import BaseModel, Field
# from agents.sql_with_preprocess.main import create_graph
# from langchain_core.messages import HumanMessage
# from agents.sql_with_preprocess.types import AgentState

# router = APIRouter()

# class ChatMessage(BaseModel):
#     role: str = Field(..., description="The role of the message sender (system/user/assistant)")
#     content: str = Field(..., description="The content of the message")
#     name: Optional[str] = Field(None, description="Optional name for the message sender")

# class ChatRequest(BaseModel):
#     model: str = Field(..., description="Model to use for completion")
#     messages: List[ChatMessage] = Field(..., description="List of messages in the conversation")
#     temperature: Optional[float] = Field(0.7, description="Sampling temperature")
#     stream: Optional[bool] = Field(False, description="Whether to stream the response")
#     max_tokens: Optional[int] = Field(None, description="Maximum tokens to generate")

# def parse_tool_calls(content: str):
#     """Parse content for tool calls and return segments"""
#     segments = []
#     current_position = 0
#     print("length of content", len(content))
#     while current_position < len(content):
#         # Look for tool call markers
#         doc_match = re.search(r'<create_doc>(.*?)</create_doc>', content[current_position:])
#         code_match = re.search(r'<create_code>(.*?)</create_code>', content[current_position:])
#         print("doc_match", doc_match)
#         print("code_match", code_match)
#         if not doc_match and not code_match:
#             remaining = content[current_position:].strip()
#             if remaining:

#                 segments.append({
#                     "type": "assistant",
#                     "content": remaining
#                 })
#             break
            
#         # Find which comes first
#         doc_start = doc_match.start() + current_position if doc_match else float('inf')
#         code_start = code_match.start() + current_position if code_match else float('inf')
        
#         # Add assistant message if there's content before tool call
#         if min(doc_start, code_start) > current_position:
#             assistant_content = content[current_position:min(doc_start, code_start)].strip()
#             if assistant_content:
#                 segments.append({
#                     "type": "assistant",
#                     "content": assistant_content
#                 })
        
#         # Add tool call
#         if doc_start < code_start:
#             segments.append({
#                 "type": "tool",
#                 "tool_call": {
#                     "id": f"call_{len(segments)}",
#                     "type": "function",
#                     "function": {
#                         "name": "createDocument",
#                         "arguments": json.dumps({
#                             "title": f"Document {len(segments)}",
#                             "kind": "text",
#                             "content": doc_match.group(1)
#                         })
#                     }
#                 }
#             })
#             current_position = doc_start + len(doc_match.group(0))
#         else:
#             segments.append({
#                 "type": "tool",
#                 "tool_call": {
#                     "id": f"call_{len(segments)}",
#                     "type": "function",
#                     "function": {
#                         "name": "createDocument",
#                         "arguments": json.dumps({
#                             "title": f"Code {len(segments)}",
#                             "kind": "code",
#                             "content": code_match.group(1)
#                         })
#                     }
#                 }
#             })
#             current_position = code_start + len(code_match.group(0))
    
#     return segments

# async def stream_response(app, initial_state) -> AsyncGenerator[str, None]:
#     response_id = f"chatcmpl-{uuid.uuid4()}"
#     created = int(__import__('time').time())

#     # Send initial role
#     initial_chunk = {
#         "id": response_id,
#         "object": "chat.completion.chunk",
#         "created": created,
#         "model": "your-model-name",
#         "choices": [{
#             "index": 0,
#             "delta": {"role": "assistant"},
#             "finish_reason": None
#         }]
#     }
#     yield f"data: {json.dumps(initial_chunk)}\n\n"

#     # Process stream from your model
#     async for val, event in app.astream(initial_state, stream_mode=["updates"]):
#         # Get content from event
#         if isinstance(list(event.values())[0]['messages'], list):
#             content = ''
#             for msg in list(event.values())[0]['messages']:
#                 content += str(msg.content) + '\n\n'
#         else:
#             content = str(list(event.values())[0]['messages'].content) + '\n\n'

#         # Parse content for segments (assistant messages and tool calls)
#         segments = parse_tool_calls(content)
        
#         # Stream each segment
#         for segment in segments:
#             if segment["type"] == "assistant":
#                 chunk = {
#                     "id": response_id,
#                     "object": "chat.completion.chunk",
#                     "created": created,
#                     "model": "your-model-name",
#                     "choices": [{
#                         "index": 0,
#                         "delta": {"content": segment["content"]},
#                         "finish_reason": None
#                     }]
#                 }
#                 yield f"data: {json.dumps(chunk)}\n\n"
#             else:  # tool call
#                 chunk = {
#                     "id": response_id,
#                     "object": "chat.completion.chunk",
#                     "created": created,
#                     "model": "your-model-name",
#                     "choices": [{
#                         "index": 0,
#                         "delta": {"tool_calls": [segment["tool_call"]]},
#                         "finish_reason": None
#                     }]
#                 }
#                 yield f"data: {json.dumps(chunk)}\n\n"

#     # Send final chunks
#     final_chunk = {
#         "id": response_id,
#         "object": "chat.completion.chunk",
#         "created": created,
#         "model": "your-model-name",
#         "choices": [{
#             "index": 0,
#             "delta": {},
#             "finish_reason": "stop"
#         }]
#     }
#     yield f"data: {json.dumps(final_chunk)}\n\n"
#     yield "data: [DONE]\n\n"

# @router.post("/v1/chat/completions")
# async def chat_endpoint(request: ChatRequest):
#     try:
#         app = await create_graph()

#         user_message = next(
#             (msg.content for msg in reversed(request.messages) if msg.role == "user"),
#             None
#         )
        
#         if not user_message:
#             raise HTTPException(status_code=400, detail="No user message found in the conversation")

#         initial_state = AgentState(
#             messages=[HumanMessage(content=user_message)],
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

#         if request.stream:
#             return StreamingResponse(
#                 stream_response(app, initial_state),
#                 media_type="text/event-stream"
#             )
#         else:
#             response_text = ""
#             async for values, event in app.astream(initial_state, stream_mode=["updates"]):
#                 if isinstance(list(event.values())[0]['messages'], list):
#                     for msg in list(event.values())[0]['messages']:
#                         response_text += str(msg.content) + '\n\n'
#                 else:
#                     response_text += str(list(event.values())[0]['messages'].content) + '\n\n'

#             # Parse content for tool calls
#             segments = parse_tool_calls(response_text)
            
#             # Collect tool calls
#             tool_calls = [s["tool_call"] for s in segments if s["type"] == "tool"]
            
#             return {
#                 "id": f"chatcmpl-{uuid.uuid4()}",
#                 "object": "chat.completion",
#                 "created": int(__import__('time').time()),
#                 "model": "your-model-name",
#                 "choices": [{
#                     "index": 0,
#                     "message": {
#                         "role": "assistant",
#                         "content": response_text,
#                         "tool_calls": tool_calls if tool_calls else None
#                     },
#                     "finish_reason": "stop"
#                 }],
#                 "usage": {
#                     "prompt_tokens": 0,
#                     "completion_tokens": 0,
#                     "total_tokens": 0
#                 }
#             }

#     except Exception as e:
#         raise HTTPException(status_code=500, detail=str(e))
