import json
import os
from typing import Dict, Any, Optional, Callable, Union
from contentcreatie.llm_client.tools.tool_base import ToolBase
from project import Project

class SaveRewrittenJsonTool(ToolBase):
    """
    A tool that allows the agent to save rewritten JSON content to a project file.
    """
    def __init__(
        self,
        project:Project,
        on_call: Optional[Callable[[Dict[str, Any]], None]] = None,
        on_result: Optional[Callable[[Dict[str, Any]], Union[str, None]]] = None,
    ):
        """Initializes the tool, passing callbacks to the base class."""
        self.project = project
        super().__init__(on_call=on_call, on_result=on_result)

    @property
    def schema(self) -> Dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": "save_rewritten_json",
                "description": "Use this tool to save rewritten JSON content for a specific project. The JSON content should be a string.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "content": {
                            "type": "string",
                            "description": "The rewritten content as a string to be saved."
                        }
                    },
                    "required": ["content"]
                }
            }
        }

    def _execute(self, **kwargs) -> str:
        """
        Updates the active project's rewritten content and saves it.

        Args:
            kwargs: Dictionary containing the parameters:
                - content: The content as a string to be saved

        Returns:
            str: A message indicating success or failure
        """
        try:
            # Extract parameters
            content = kwargs.get("content")

            if not content:
                return f"Error: No JSON content provided for project {self.project.id}."

            self.project.rewritten_json = content
            self.project.rewritten_text = content

            return f"Rewritten JSON content for project {self.project.id} updated and saved successfully."
        except Exception as e:
            return f"Error updating rewritten JSON content for project {self.project.id}: {e}"
