import json
from typing import Any, Dict, Optional
from project import Project

def streamlit_tool_callback(tool_call: Dict[str, Any], project: "Project"):
    """Callback die de UI van een specifiek project bijwerkt."""
    function_name = tool_call.get('function', {}).get('name')
    try:
        args = json.loads(tool_call.get('function', {}).get('arguments', '{}'))
    except json.JSONDecodeError:
        args = {}

    if function_name == "update_document_shortlist":
        for score_info in args.get("scores", []):
            doc_id = score_info.get('document_id')
            project.upsert_document(doc_id,score_info.get('score'))

    elif function_name == "update_scratchpad":
        project.scratchpad = args.get("tasks", [])
        

def streamlit_tool_result_callback(tool_result: Dict[str, Any], project: "Project") -> Optional[str]:
    """Callback die de resultaten van een tool verwerkt voor een specifiek project."""
    function_name = tool_result.get("function_name")

    if function_name == "vector_search":
        try:
            documents = json.loads(tool_result.get("output", "[]"))
            if not isinstance(documents, list):
                return None
            for doc_info in documents:
                doc_id = doc_info.get('id')
                project.upsert_document(doc_id=doc_id)
        except (json.JSONDecodeError, AttributeError):
            pass
    return None