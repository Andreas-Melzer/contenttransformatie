import json
from typing import Dict, Any, List, Optional, Callable, Union
from contentcreatie.llm_client.tools.tool_base import ToolBase

class ListSelectedDocumentsTool(ToolBase):
    """
    A tool that allows the agent to list all KM numbers that have been selected
    by either the agent or the user.
    """
    def __init__(
        self,
        on_call: Optional[Callable[[Dict[str, Any]], None]] = None,
        on_result: Optional[Callable[[Dict[str, Any]], Union[str, None]]] = None,
    ):
        """Initializes the tool, passing callbacks to the base class."""
        super().__init__(on_call=on_call, on_result=on_result)

    @property
    def schema(self) -> Dict[str, Any]:
        """Defines the schema for the list selected documents tool."""
        return {
            "type": "function",
            "function": {
                "name": "list_selected_documents",
                "description": "Use this tool to get a list of all KM numbers that have been selected by either the agent or the user. This includes documents found through agent searches and user searches.",
                "parameters": {
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            }
        }

    def _execute(self, **kwargs) -> str:
        """
        The logic is handled by the 'on_call' callback in the Streamlit app.
        This method simply returns a confirmation message to the agent.
        """
        print("Executing ListSelectedDocumentsTool")
        # The actual implementation will be provided by the on_call callback
        # This is just a placeholder return value
        return json.dumps({
            "agent_found": [],
            "user_found": []
        })