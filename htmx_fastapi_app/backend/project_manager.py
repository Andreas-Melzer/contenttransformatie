from typing import Dict, Any

# In-memory dictionary to store projects.
# For production, replace this with a database (e.g., SQLite, PostgreSQL).
PROJECTS_DB: Dict[str, Dict[str, Any]] = {}

def initialize_projects():
    """Initializes the project database if it's empty."""
    if not PROJECTS_DB:
        PROJECTS_DB.clear()

def create_project(project_id: str, vraag: str):
    """Creates a new, empty project in the database."""
    if project_id in PROJECTS_DB:
        raise ValueError("Project with this ID already exists.")
    
    PROJECTS_DB[project_id] = {
        "id": project_id,
        "vraag": vraag,
        "messages": [{"role": "assistant", "content": f"Oké, ik start het onderzoek voor de vraag: '{vraag}'. Laten we beginnen."}],
        "shortlist": {},
        "selected_doc_id": None,
        "scratchpad": [],
        "consolidated_content": None,
        "rewritten_content": None,
        "validated": False
    }

def get_all_projects() -> Dict[str, Dict[str, Any]]:
    """Retrieves all projects from the database."""
    return PROJECTS_DB

def get_project_by_id(project_id: str) -> Dict[str, Any]:
    """Retrieves a single project by its ID."""
    return PROJECTS_DB.get(project_id)

def add_user_message_to_project(project_id: str, content: str):
    """Adds a user message to a project's message history."""
    project = get_project_by_id(project_id)
    if project:
        project["messages"].append({"role": "user", "content": content})

def add_assistant_response_to_project(project_id: str, content: str):
    """Adds an assistant's response to a project's message history."""
    project = get_project_by_id(project_id)
    if project:
        project["messages"].append({"role": "assistant", "content": content})

def update_project_scratchpad(project_id: str, scratchpad: list):
    """Updates the scratchpad for a specific project."""
    project = get_project_by_id(project_id)
    if project:
        project["scratchpad"] = scratchpad