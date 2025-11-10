import json
from typing import Dict, Any, List, Optional, Callable, Union
from contentcreatie.llm_client.tools.tool_base import ToolBase
from contentcreatie.llm_client.document_store import DocumentStore

class ReadDocumentsTool(ToolBase):
    """
    A tool that allows the agent to read the content of one or more documents by providing their KM numbers.
    """
    def __init__(
        self,
        doc_store: DocumentStore,
        on_call: Optional[Callable[[Dict[str, Any]], None]] = None,
        on_result: Optional[Callable[[Dict[str, Any]], Union[str, None]]] = None,
    ):
        """Initializes the tool, passing callbacks to the base class."""
        super().__init__(on_call=on_call, on_result=on_result)
        self.doc_store = doc_store

    @property
    def schema(self) -> Dict[str, Any]:
        """Defines the schema for the read documents tool."""
        return {
            "type": "function",
            "function": {
                "name": "read_documents",
                "description": "Use this tool to read the content of one or more documents by providing their KM numbers. The tool returns the document content and metadata.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "document_ids": {
                            "type": "array",
                            "description": "A list of KM numbers for the documents to read.",
                            "items": {
                                "type": "string"
                            }
                        }
                    },
                    "required": ["document_ids"]
                }
            }
        }

    def _execute(self, document_ids: List[str]) -> str:
        """
        Reads documents from the document store using the provided KM numbers.
        """
        documents = []
        for doc_id in document_ids:
            doc = self.doc_store.documents.get(doc_id)
            if doc:
                documents.append({
                    "document_id": doc.id,
                    "title": doc.title,
                    "content": doc.content,
                    "metadata": doc.metadata
                })
            else:
                documents.append({
                    "document_id": doc_id,
                    "error": "Document not found"
                })

        return json.dumps({"documents": documents}, indent=2)