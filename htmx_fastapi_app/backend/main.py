import uvicorn
import uuid
from fastapi import FastAPI, Request, Form, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from typing import Dict, Any

from backend.project_manager import (
    get_all_projects,
    create_project,
    get_project_by_id,
    add_user_message_to_project,
    add_assistant_response_to_project,
    update_project_scratchpad
)
from backend.llm_integration import (
    load_agent_and_doc_store, 
    run_agent_chat
)

app = FastAPI()

# --- App Configuration ---
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# In a real application, consider loading these once at startup
# For simplicity here, we load them when needed.
agent, doc_store = None, None

@app.on_event("startup")
async def startup_event():
    """Load heavy components on startup."""
    global agent, doc_store
    # Note: project-specific callbacks need to be handled differently.
    # We will pass project state directly to the functions.
    agent, doc_store = load_agent_and_doc_store()


# --- HTML Serving Routes ---

@app.get("/", response_class=HTMLResponse)
async def get_project_dashboard(request: Request):
    """Serves the main project dashboard page."""
    projects = get_all_projects()
    return templates.TemplateResponse("index.html", {
        "request": request,
        "projects": projects
    })

@app.get("/project/{project_id}", response_class=HTMLResponse)
async def get_project_page(request: Request, project_id: str):
    """Serves the detailed page for a single project."""
    project = get_project_by_id(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    return templates.TemplateResponse("project_detail.html", {
        "request": request,
        "project": project,
        "doc_store": doc_store # Pass doc_store for rendering
    })


# --- HTMX API Endpoints ---

@app.post("/projects", response_class=HTMLResponse)
async def handle_create_project(request: Request, project_question: str = Form(...)):
    """Creates a new project and returns the updated project list."""
    if project_question:
        project_id = str(uuid.uuid4())
        create_project(project_id, project_question)
    
    projects = get_all_projects()
    return templates.TemplateResponse("partials/project_list.html", {
        "request": request,
        "projects": projects
    })

@app.post("/project/{project_id}/chat", response_class=HTMLResponse)
async def handle_chat_message(request: Request, project_id: str, prompt: str = Form(...)):
    """Handles a new chat message, runs the agent, and returns the updated UI."""
    project = get_project_by_id(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # 1. Add user message to project
    add_user_message_to_project(project_id, prompt)
    
    # 2. Run the agent logic
    final_response, updated_shortlist, updated_scratchpad = run_agent_chat(
        agent=agent,
        project=project,
        query=prompt
    )
    
    # 3. Update project state with agent's results
    add_assistant_response_to_project(project_id, final_response)
    update_project_scratchpad(project_id, updated_scratchpad)
    
    # The shortlist is updated via the callback mechanism inside `run_agent_chat`
    
    # 4. Return updated components
    return templates.TemplateResponse("project_detail.html", {
        "request": request,
        "project": get_project_by_id(project_id), # Fetch updated project
        "doc_store": doc_store
    })

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)