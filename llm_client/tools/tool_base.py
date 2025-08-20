from abc import ABC, abstractmethod
from typing import Dict, Any, Callable, Optional, Union
import json

class ToolBase(ABC):
    """
    Abstract base class for creating a runnable tool for the agent.
    A tool can be initialized with optional callbacks for pre- and post-execution hooks.
    """
    def __init__(
        self,
        on_call: Optional[Callable[[Dict[str, Any]], None]] = None,
        on_result: Optional[Callable[[Dict[str, Any]], Union[str, None]]] = None,
    ):
        """
        Initializes the tool with optional callbacks.

        :param on_call: A callback function executed before the tool runs. Receives a dictionary with tool call details.
        :param on_result: A callback function executed after the tool runs. Receives a dictionary with the result and can return a string to override the tool's output.
        """
        self.on_call = on_call
        self.on_result = on_result

    @property
    @abstractmethod
    def schema(self) -> Dict[str, Any]:
        """
        The tool's schema in OpenAI's JSON format.
        :return: Dict[str, Any], The schema dictionary.
        """
        pass

    @abstractmethod
    def _execute(self, **kwargs) -> str:
        """
        Executes the tool's core logic. This method should be implemented by child classes.
        :param kwargs: The arguments for the function, as defined in the schema.
        :return: The string result of the tool's execution.
        """
        pass

    def execute(self, **kwargs) -> str:
        """
        A wrapper that executes the tool's logic and handles the callbacks.
        This method should not be overridden by child classes.
        """
        # 1. Pre-execution callback (for logging, UI updates, etc.)
        if self.on_call:
            try:
                # Reconstruct the tool_call object the agent originally provided
                tool_call_info = {
                    "function": {
                        "name": self.schema['function']['name'],
                        "arguments": json.dumps(kwargs)
                    }
                }
                self.on_call(tool_call_info)
            except Exception as e:
                print(f"Error in 'on_call' callback for tool '{self.schema['function']['name']}': {e}")
        
        # 2. Core logic execution
        result = self._execute(**kwargs)

        # 3. Post-execution callback (can modify the result)
        if self.on_result:
            try:
                # Reconstruct the result object the agent originally provided
                tool_result_info = {
                    "function_name": self.schema['function']['name'],
                    "arguments": kwargs,
                    "output": result
                }
                override_result = self.on_result(tool_result_info)
                if override_result is not None:
                    return override_result
            except Exception as e:
                print(f"Error in 'on_result' callback for tool '{self.schema['function']['name']}': {e}")
            
        return result
