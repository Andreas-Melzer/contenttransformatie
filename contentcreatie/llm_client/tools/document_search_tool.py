import json
from typing import Dict, Any, Optional, Callable, Union
from .tool_base import ToolBase
from ..document_vector_store import DocumentStore

class DocumentSearchTool(ToolBase):
    """A tool for performing structured metadata searches on a DocumentStore."""

    def __init__(
        self,
        doc_store: DocumentStore,
        on_call: Optional[Callable[[Dict[str, Any]], None]] = None,
        on_result: Optional[Callable[[Dict[str, Any]], Union[str, None]]] = None,
    ):
        """Initializes the tool, passing callbacks to the base class."""
        super().__init__(on_call=on_call, on_result=on_result)
        self.doc_store = doc_store
        self.indexed_metadata_keys = self.doc_store.indexed_metadata_keys

    @property
    def schema(self) -> Dict[str, Any]:
        """The schema definition, with a dynamic description of searchable fields."""
        description = (
            f"Performs a structured search on document metadata. Available fields: {', '.join(self.indexed_metadata_keys)}. "
            "Use Whoosh syntax like 'status:approved AND category:feature'."
        ) if self.indexed_metadata_keys else "Performs a structured search. NOTE: No metadata fields are indexed."

        return {
            "type": "function", "function": {
                "name": "metadata_search", "description": description,
                "parameters": {
                    "type": "object", "properties": {
                        "query_string": {"type": "string", "description": "The search query using Whoosh syntax."}
                    }, "required": ["query_string"]
                }
            }
        }

    def _execute(self, query_string: str) -> str:
        """Executes a search on the DocumentStore's metadata index."""
        if not self.indexed_metadata_keys:
            return "Cannot perform search: no metadata fields were indexed for this DocumentStore."

        results = self.doc_store.search(query_string=query_string, limit=5)
        if not results: return "No documents found matching the query."

        simplified_results = [{
            "id": doc.id,
            "title": doc.title,
            "content_snippet" : doc.content[0:250] + " .....",
            "metadata": {k:v for k,v in doc.metadata.items() if k != 'full_text'}
        } for doc in results]

        return json.dumps(simplified_results, indent=2)