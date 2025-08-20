import streamlit as st

def initialize_session_state():
    """Initializes all necessary session state variables if they don't exist."""
    if "messages" not in st.session_state:
        st.session_state.messages = [{"role": "assistant", "content": "Goedendag! Wat kan ik voor u zoeken?"}]
    if "shortlist" not in st.session_state:
        st.session_state.shortlist = {}
    if "selected_doc_id" not in st.session_state:
        st.session_state.selected_doc_id = None
    if "scratchpad" not in st.session_state:
        st.session_state.scratchpad = []

def get_or_create_agent_scratchpad():
    """Safely retrieves or initializes the agent's scratchpad in the session state."""
    if "scratchpad" not in st.session_state:
        st.session_state.scratchpad = []
    return st.session_state.scratchpad