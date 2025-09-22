import json
import os
from typing import Dict, Any, Optional, Callable, Union
from llm_client.tools.tool_base import ToolBase
from interface.project import Project

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
        """Defines the schema for the save rewritten JSON tool."""
        return {
            "type": "function",
            "function": {
                "name": "save_rewritten_json",
                "description": "Use this tool to save rewritten JSON content for a specific project. The JSON content should be a string.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        # "project_id": {
                        #     "type": "string",
                        #     "description": "The unique identifier of the project."
                        # },
                        "json_content": {
                            "type": "string",
                            "description": "The JSON content as a string to be saved."
                        }
                    },
                    "required": ["project_id", "json_content"]
                }
            }
        }

    def _execute(self, json_content: str) -> str:
        """
        Updates the active project's rewritten JSON content and saves it.
        """
        try:

            rewritten_data = json.loads(json_content)
            self.project.rewritten_json = rewritten_data
            self.project.rewritten_text = rewritten_data.get('content', '') # Also update rewritten_text for display
            # The setter for rewritten_json automatically calls active_project.save()

            return f"Rewritten JSON content for project {self.project.id} updated and saved successfully."
        except json.JSONDecodeError:
            return f"Error: Invalid JSON content provided for project {self.project.id}."
        except Exception as e:
            return f"Error updating rewritten JSON content for project {self.project.id}: {e}"
