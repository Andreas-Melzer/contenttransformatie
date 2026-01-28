import json
from typing import Dict, Any, List, Union, Optional, Callable
from contentcreatie.llm_client.tools.tool_base import ToolBase
from contentcreatie.llm_client.vector_store import VectorStore

class VectorSearchTool(ToolBase):
    """
    A tool for performing semantic vector searches on a VectorStore.
    Can accept a single query or a list of queries.
    """
    def __init__(
        self,
        vector_store: VectorStore,
        on_call: Optional[Callable[[Dict[str, Any]], None]] = None,
        on_result: Optional[Callable[[Dict[str, Any]], Union[str, None]]] = None,
        metadata_filter: Optional[Dict[str, Any]] = None,
    ):
        """
        Initializes the tool with a VectorStore instance and optional callbacks.
        """
        super().__init__(on_call=on_call, on_result=on_result)
        self.vector_store = vector_store
        self.metadata_filter = metadata_filter

    @property
    def schema(self) -> Dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": "vector_search",
                "description": "Finds documents with content semantically similar to one or more query texts. Returns a deduplicated list of the best matches.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "queries": {
                            "oneOf": [
                                {"type": "string", "description": "A single descriptive query text."},
                                {"type": "array", "description": "A list of descriptive query texts.", "items": {"type": "string"}}
                            ],
                            "description": "The query or list of queries to search for."
                        },
                        "n_results": {"type": "integer", "description": "The number of top matching documents to return per query.", "default": 5}
                    },
                    "required": ["queries"]
                }
            }
        }

    def _execute(self, queries: Union[str, List[str]], n_results: int = 5) -> str:
        """Searches the VectorStore and returns deduplicated results as a JSON string."""
        query_list = queries if isinstance(queries, list) else [queries]
        best_results = {}
        for query_index, query_text in enumerate(query_list):
            results = self.vector_store.query(query_text=query_text, n_results=n_results, metadata_filter=self.metadata_filter)
            if not results: continue

            for res in results:
                doc = res['document']
                doc_id = doc.metadata.get('km_number', doc.id)
                current_distance = res['distance']

                if doc_id not in best_results or current_distance < best_results[doc_id]['distance']:
                    best_results[doc_id] = {
                        "id": doc_id,
                        "title": doc.title,
                        "content_snippet": (doc.content[:5000] + " ...") if doc.content else "",
                        "metadata": {k: v for k, v in doc.metadata.items() if k in ['BELASTINGSOORT', 'PROCES_ONDERWERP','PRODUCT_SUBONDERWERP', 'VRAAG']},
                        "distance": current_distance,
                        "query_number": query_index
                    }

        if not best_results:
            return "No documents found for any of the provided queries."

        simplified_results = sorted(list(best_results.values()), key=lambda x: x['distance'])
        return json.dumps(simplified_results, indent=2)