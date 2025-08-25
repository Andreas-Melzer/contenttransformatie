import streamlit as st

def initialize_session_state():
    """Initializes all necessary session state variables if they don't exist."""
    if "projects" not in st.session_state:
        st.session_state.projects = {}
    if "active_project_id" not in st.session_state:
        st.session_state.active_project_id = None