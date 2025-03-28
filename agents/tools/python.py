from langchain.tools import BaseTool, StructuredTool, tool
from langchain_experimental.utilities import PythonREPL
from langchain_core.tools import Tool
import os
from datetime import datetime
import cloudinary
import cloudinary.uploader
from dotenv import load_dotenv
import matplotlib.pyplot as plt
import numpy as np
import io
load_dotenv()
# Configure Cloudinary
cloudinary.config(
    cloud_name = os.environ.get('CLOUDINARY_CLOUD_NAME'),
    api_key = os.environ.get('CLOUDINARY_API_KEY'),
    api_secret = os.environ.get('CLOUDINARY_API_SECRET')
)

python_repl = PythonREPL()

def upload_to_cloudinary(image_data: bytes, filename: str) -> str:
    """Upload image to Cloudinary and return the URL"""
    try:
        # Upload to cloudinary
        result = cloudinary.uploader.upload(
            image_data,
            public_id=filename,
            folder="matplotlib_plots",  # Optional: organize in folder
            resource_type="image"
        )
        # Return the secure URL
        return result['secure_url']
    except Exception as e:
        return f"Error uploading to Cloudinary: {str(e)}"

def execute_code(code:str)->str:
    """Execute Python code using a REPL environment.
    
    Args:
        code (str): The Python code to execute
        
    Returns:
        str: The output of the executed code or the public url of  the saved image
    """
    try:
        if "matplotlib" in code.lower() and ("plt" in code.lower() or "show" in code.lower()):
            # Preconfigure environment before any imports
            
            modified_code = (
                "import os\n"
                "os.environ['MPLBACKEND'] = 'Agg'\n"
                "import matplotlib\n"
                "matplotlib.use('Agg')\n\n"
                + code
            )
            exec(modified_code)
            print('Code :',code)
            # Save plot to buffer
            buf = io.BytesIO()
            plt.savefig(buf, format='png')
            plt.close()
            buf.seek(0)
            
            # Upload to Cloudinary
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            result= upload_to_cloudinary(buf.getvalue(), f'plot_{timestamp}')
            print("Result: ",result)
            return result
        else:
            return "Couldn't upload the plot online"
            
        return python_repl.run(code)
    except Exception as e:
        # Catch and return any exceptions that occur during code execution
        return f"Error executing code: {str(e)}"

python = Tool(
    # func=python_repl.run,
    func=execute_code,
    name="Python",
    description="A Python code interpeter for visualising data that excutes code and uploads the plt to website and gives back url. Use this to execute visualise data.",
    # coroutine= ... <- you can specify an async method if desired as well
)

def test_execute_code():
    """
    Test function to demonstrate and verify the execute_code functionality.
    This will test various scenarios like basic Python execution, 
    matplotlib plotting, and error handling.
    """
    # Test basic Python execution
    basic_code = "print('Hello, World!')\nx = 5 + 3\nprint(x)"
    print("Basic Python Execution Test:")
    result = execute_code(basic_code)
    print(result)

    # Test matplotlib plotting
    matplotlib_code = """
import matplotlib.pyplot as plt
import numpy as np

# Create a simple line plot with error handling
try:
    x = np.linspace(0, 10, 100)
    y = np.sin(x)

    plt.figure(figsize=(10, 6))
    plt.plot(x, y)
    plt.title('Sine Wave')
    plt.xlabel('X axis')
    plt.ylabel('Y axis')
    plt.grid(True)
except Exception as e:
    print(f"Error in matplotlib plotting: {str(e)}")
"""
    print("\nMatplotlib Plotting Test:")
    result = execute_code(matplotlib_code)
    print(f"Cloudinary URL for plot: {result}")

    # Test error handling
    # error_code = "1 / 0  # This will raise a ZeroDivisionError"
    # print("\nError Handling Test:")
    # result = execute_code(error_code)
    # print(result)

# Uncomment the line below to run tests when this module is executed directly
# test_execute_code()
