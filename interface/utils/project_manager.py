import streamlit as st
from interface.project import Project
from interface.utils.component_loader import load_heavy_components, initialize_agent_for_project

def create_project(project_id: str, vraag: str):
    """Maakt een nieuw project aan, initialiseert de agent en voegt het toe aan de session state."""
    # Stap 1: Laad de zware, gedeelde componenten (gecached)
    llm, _, vector_store = load_heavy_components()
    project = Project(vraag, project_id)
    project.agent = initialize_agent_for_project(project, llm, vector_store)
    st.session_state.projects[project_id] = project

def get_all_projects():
    """Haalt alle projecten op."""
    return st.session_state.get("projects", {})

def get_active_project() -> Project | None:
    """Haalt het momenteel actieve project op."""
    active_id = st.session_state.get("active_project_id")
    if active_id and active_id in st.session_state.get("projects", {}):
        return st.session_state.projects[active_id]
    return None