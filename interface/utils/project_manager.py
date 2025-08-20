import streamlit as st

def initialize_projects():
    """Initialiseert de projectenlijst in de session state."""
    if "projects" not in st.session_state:
        st.session_state.projects = {}
    if "active_project_id" not in st.session_state:
        st.session_state.active_project_id = None

def create_project(project_id: str, vraag: str):
    """Maakt een nieuw, leeg project aan."""
    st.session_state.projects[project_id] = {
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

def get_all_projects():
    """Haalt alle projecten op."""
    return st.session_state.get("projects", {})

def get_active_project():
    """Haalt het momenteel actieve project op."""
    active_id = st.session_state.get("active_project_id")
    if active_id and active_id in st.session_state.get("projects", {}):
        return st.session_state.projects[active_id]
    return None