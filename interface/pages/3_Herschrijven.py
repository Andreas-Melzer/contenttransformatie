import streamlit as st
from interface.utils.component_loader import load_heavy_components
from interface.utils.project_manager import get_active_project
from llm_client.llm_client import json_decode
import json
from interface.implementations.tools.save_rewritten_json_tool import SaveRewrittenJsonTool
from interface.components.clear_agent_messages import display_clear_agent_messages_button
from interface.components.agent_sidebar_component import display_agent_sidebar

active_project = get_active_project()
st.set_page_config(layout="wide", page_title="Herschrijven")

# Load components
_, doc_store, vector_store = load_heavy_components()

# Display agent sidebar
display_agent_sidebar(active_project, agent_name="rewrite_agent")

st.title(f"Project: \"{active_project.vraag}\"")
st.header("Stap 3: Herschrijven van Geconsolideerde Content")

# Check if we have consolidated content
if not active_project.consolidated_json:
    st.info("Er is nog geen geconsolideerde content. Ga terug naar de consolidatie stap om content te consolideren.")
else:
    # Create tabs for different sections
    tab1, tab2 = st.tabs(["Geconsolideerde Content", "Herschreven Content"])
    
    # Tab 1: Show consolidated content
    with tab1:
        st.subheader("Geconsolideerde Content")
        if active_project.consolidated_json:
            # Display consolidated content in a readable format
            consolidated_data = active_project.consolidated_json
            st.json(consolidated_data)
        else:
            st.info("Er is nog geen geconsolideerde content beschikbaar.")
            
# Add button to clear agent messages in the sidebar
with st.sidebar:
    display_clear_agent_messages_button(active_project, "rewrite_agent")

    # Button to start automatic rewriting
    if st.button("Start Automatisch Herschrijven", type="primary"):
        # Add a message to trigger rewriting
        rewrite_prompt = f"Ik wil graag de geconsolideerde content herschrijven voor de vraag: \"{active_project.vraag}\"."
        active_project.rewrite_messages = active_project.rewrite_messages + [{"role": "user", "content": rewrite_prompt}]
        st.rerun()
    
    # Tab 3: Show rewritten content
    with tab2:
        st.subheader("Herschreven Content")
        if active_project.rewritten_text:
            st.markdown(active_project.rewritten_text)
        else:
            st.info("Er is nog geen herschreven content. Gebruik de herschrijf agent om content te genereren.")