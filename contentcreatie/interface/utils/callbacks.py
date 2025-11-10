import json
from typing import Any, Dict, Optional
from project import Project

def streamlit_tool_callback(tool_call: Dict[str, Any], project: Project):
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
        
def list_documents_callback(tool_result: Dict[str, Any], project):
    """
    Callback function for the list_selected_documents tool.
    Returns the list of all selected documents (both agent-found and user-found).
    """
    all_documents = {
        "agent_found": list(project.agent_found_documents.keys()),
        "user_found": list(project.self_found_documents.keys())
    }

    return json.dumps(all_documents)       


def search_results_callback(tool_result: Dict[str, Any], project: Project) -> Optional[str]:
        try:
            documents = json.loads(tool_result.get("output", "[]"))
            if not isinstance(documents, list):
                return None
            for doc_info in documents:
                doc_id = doc_info.get('id')
                project.upsert_document(doc_id=doc_id)
        except (json.JSONDecodeError, AttributeError):
            pass