import streamlit as st
from interface.utils.project_manager import load_all_projects

def initialize_session_state():
    """Initializes all necessary session state variables if they don't exist."""
    if "projects" not in st.session_state:
        st.session_state.projects = load_all_projects()
    if "active_project_id" not in st.session_state:
        st.session_state.active_project_id = None