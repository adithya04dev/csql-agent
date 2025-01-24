import io
import base64
from langchain.chat_models import ChatOpenAI
from langchain.prompts import PromptTemplate
from langchain.schema import HumanMessage, AIMessage, SystemMessage
import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd

# Initialize the LLM
llm = ChatOpenAI(openai_api_key="YOUR_API_KEY", model_name="gpt-3.5-turbo")

def generate_visualization_code(messages):
    """
    Prompts the LLM to generate visualization code directly from the message history,
    and returns the code.

    Args:
        messages: A list of LangChain ChatMessage objects representing the conversation history.

    Returns:
        A string containing the generated Python code, or None if an error occurs.
    """

    # Prompt template for generating the visualization code
    code_generation_template = """
    You are a data visualization expert. You will be provided with a conversation history.
    Your task is to generate Python code using Matplotlib and Seaborn for data visualization based on the data in the conversation history.

    The code should be self-contained and executable. It should:
      - Create a Pandas DataFrame if necessary, based on the data in the conversation.
      - Use the `data` variable for the DataFrame if applicable.
      - Generate a suitable visualization based on the data.
      - Not include any comments in the code.
      - Create a new figure using `plt.figure()`.
      - Save the plot to a file called 'output.png' using `plt.savefig('output.png')`.

    Conversation History:
    {history}

    Python code:
    """

    code_generation_prompt = PromptTemplate(
        input_variables=["history"], template=code_generation_template
    )

    # Format the conversation history
    formatted_history = ""
    for msg in messages:
        if isinstance(msg, HumanMessage):
            formatted_history += f"Human: {msg.content}\n"
        elif isinstance(msg, AIMessage):
            formatted_history += f"AI: {msg.content}\n"
        elif isinstance(msg, SystemMessage):
            formatted_history += f"System: {msg.content}\n"

    # Get code from LLM using a single call
    code_generation_request = code_generation_prompt.format_prompt(history=formatted_history)
    code_response = llm([code_generation_request.to_messages()[0]]).content

    return code_response

def get_visualization_image_and_update_history(messages):
    """
    Generates visualization code, executes it, captures the image, 
    updates the message history, and returns the Base64 image string.

    Args:
        messages: A list of LangChain ChatMessage objects.

    Returns:
        A tuple: (Base64 encoded image string, updated messages list), 
        or (None, original messages list) if an error occurs.
    """
    llm_generated_code = generate_visualization_code(messages)

    if llm_generated_code:
        try:
            # Create a limited scope for exec()
            local_vars = {"plt": plt, "sns": sns, "pd": pd}

            # Execute the code
            exec(llm_generated_code, {}, local_vars)

            # Capture the plot in an in-memory stream
            img_buffer = io.BytesIO()
            plt.savefig(img_buffer, format="png")
            plt.close()  # Close the plot to free resources
            img_buffer.seek(0)

            # Encode the image data to Base64
            img_base64 = base64.b64encode(img_buffer.read()).decode("utf-8")

            # Update message history
            messages.append(AIMessage(content=llm_generated_code))  # Add generated code
            messages.append(AIMessage(content=f"data:image/png;base64,{img_base64}"))  # Add image

            return img_base64, messages

        except Exception as e:
            print(f"Error generating visualization: {e}")
            return None, messages
    else:
        print("Code generation failed.")
        return None, messages

# Example Usage (with dummy message history)
messages = [
    HumanMessage(content="Here's some data: apples 5, oranges 2, bananas 8"),
    AIMessage(content="Okay, I understand."),
]

image_base64, updated_messages = get_visualization_image_and_update_history(messages)

if image_base64:
    print("Image generated and encoded. (First 100 characters of Base64):", image_base64[:100])
    # Further processing with updated_messages, e.g., display in frontend
else:
    print("Image generation failed.")