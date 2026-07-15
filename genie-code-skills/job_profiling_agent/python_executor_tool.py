import sys
import io
import traceback
from typing import str

def execute_databricks_python(code_string: str) -> str:
    """
    Executes Python code dynamically in the Databricks environment and returns the standard output.
    The Agent uses this tool to execute the WorkspaceClient and REST API scripts it generates.
    
    Args:
        code_string (str): The Python script to execute.
        
    Returns:
        str: The printed output or the stack trace if an error occurs.
    """
    # Redirect standard output to capture print() statements from the agent's code
    old_stdout = sys.stdout
    redirected_output = sys.stdout = io.StringIO()
    
    try:
        # Define a clean global namespace for the execution
        exec_globals = {
            "__builtins__": __builtins__
        }
        
        # Execute the dynamically generated code
        exec(code_string, exec_globals)
        
        # Capture the output
        output = redirected_output.getvalue()
        
        if not output.strip():
            return "Code executed successfully, but returned no printed output."
            
        return output
        
    except Exception as e:
        # If the agent's code fails, return the full traceback so it can self-correct (ReAct)
        error_msg = traceback.format_exc()
        return f"Execution Failed. Analyze this stack trace and fix your code:\n{error_msg}"
        
    finally:
        # Always restore stdout
        sys.stdout = old_stdout
