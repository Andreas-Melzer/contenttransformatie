import json
from typing import Dict, Any, List, Optional, Callable, Union
from contentcreatie.llm_client.tools.tool_base import ToolBase

class DocumentRelevanceTool(ToolBase):
    """
    A tool that allows the agent to update relevance scores for documents in a shortlist.
    The app intercepts this tool call to update the UI via an 'on_call' callback.
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
        """Defines the schema for the document shortlist tool."""
        return {
            "type": "function",
            "function": {
                "name": "update_document_shortlist",
                "description": "Use this tool to update the relevance scores for documents already shown to the user. This is used for ranking.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "scores": {
                            "type": "array",
                            "description": "A list of documents and their corresponding relevance scores.",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "document_id": {
                                        "type": "string",
                                        "description": "The unique id of the document (id returned by vector search tool looks like KM******)."
                                    },
                                    "score": {
                                        "type": "integer",
                                        "description": "A relevance score from 0 (not relevant) to 5 (highly relevant)."
                                    }
                                },
                                "required": ["document_id", "score"]
                            }
                        }
                    },
                    "required": ["scores"]
                }
            }
        }

    def _execute(self, scores: List[Dict]) -> str:
        """
        The logic is handled by the 'on_call' callback in the Streamlit app.
        This method simply returns a confirmation message to the agent.
        """
        print(f"Executing DocumentShortlistTool with scores for {len(scores)} documents.")
        return f"The shortlist was successfully updated with relevance scores for {len(scores)} document(s)."