# backend/utils/callbacks.py
import json
from typing import Any, Dict, Optional

def tool_callback(tool_call: Dict[str, Any], project: Dict):
    """Callback that updates the project state based on a tool call."""
    function_name = tool_call.get('function', {}).get('name')
    try:
        args = json.loads(tool_call.get('function', {}).get('arguments', '{}'))
    except json.JSONDecodeError:
        args = {}

    if function_name == "update_document_shortlist":
        for score_info in args.get("scores", []):
            doc_id = score_info.get('document_id')
            if doc_id and doc_id in project["shortlist"]:
                project["shortlist"][doc_id]['relevance'] = score_info.get('score')

    elif function_name == "update_scratchpad":
        project["scratchpad"] = args.get("tasks", [])

def tool_result_callback(tool_result: Dict[str, Any], project: Dict) -> Optional[str]:
    """Callback that processes tool results and updates the project state."""
    function_name = tool_result.get("function_name")

    if function_name == "vector_search":
        try:
            documents = json.loads(tool_result.get("output", "[]"))
            if not isinstance(documents, list):
                return None
            for doc_info in documents:
                doc_id = doc_info.get('id')
                if doc_id and doc_id not in project["shortlist"]:
                    project["shortlist"][doc_id] = {'relevance': None}
        except (json.JSONDecodeError, AttributeError):
            pass
    return None