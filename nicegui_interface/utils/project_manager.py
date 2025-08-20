import uuid
from typing import Dict, Any, Optional

# Global storage for projects (in a real app, this would be a database)
_projects = {}
_active_project_id = None

def initialize_projects():
    """Initialiseert de projectenlijst."""
    global _projects, _active_project_id
    if _projects is None:
        _projects = {}
    if _active_project_id is None:
        _active_project_id = None

def create_project(project_id: str, vraag: str):
    """Maakt een nieuw, leeg project aan."""
    global _projects
    _projects[project_id] = {
        "id": project_id,
        "vraag": vraag,
        "messages": [{"role": "assistant", "content": f"Oké, ik start het onderzoek voor de vraag: '{vraag}'. Laten we beginnen."}],
        "shortlist": {},
        "selected_doc_id": None,
        "scratchpad": [],
        # Voorbereid voor toekomstige stappen
        "consolidated_content": None,
        "rewritten_content": None,
        "validated": False
    }

def get_all_projects() -> Dict[str, Any]:
    """Haalt alle projecten op."""
    global _projects
    return _projects

def get_project(project_id: str) -> Optional[Dict[str, Any]]:
    """Haalt een specifiek project op."""
    global _projects
    return _projects.get(project_id)

def update_project(project_id: str, project_data: Dict[str, Any]):
    """Update een project."""
    global _projects
    _projects[project_id] = project_data

def get_active_project_id() -> Optional[str]:
    """Haalt het momenteel actieve project ID op."""
    global _active_project_id
    return _active_project_id

def set_active_project_id(project_id: str):
    """Stelt het momenteel actieve project in."""
    global _active_project_id
    _active_project_id = project_id