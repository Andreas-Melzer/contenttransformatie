import streamlit as st
from utils.project_manager import get_active_project
from components.agent_sidebar_component import display_agent_sidebar

active_project = get_active_project()

st.title(f"Project: \"{active_project.vraag}\"")
st.header("Stap 3: Herschrijven van Geconsolideerde Content")

# Check if we have consolidated content
if not active_project.consolidated_json:
    st.info("Er is nog geen geconsolideerde content. Ga terug naar de consolidatie stap om content te consolideren.")
else:
    tab1, tab2 = st.tabs(["Geconsolideerde Content", "Herschreven Content"])
    with tab1:
        st.subheader("Geconsolideerde Content")
        if active_project.consolidated_json:
            # Display consolidated content in a readable format
            consolidated_data = active_project.consolidated_json
            st.json(consolidated_data)
        else:
            st.info("Er is nog geen geconsolideerde content beschikbaar.")
    with tab2:
        st.subheader("Herschreven Content")
   
        if active_project.rewritten_text:
            st.markdown(active_project.rewritten_text)
        else:
            st.info("Er is nog geen herschreven content. Gebruik de herschrijf agent om content te genereren.")        

    display_agent_sidebar(active_project, agent_type="rewrite") 
    with st.sidebar:
        if st.button("Start Automatisch Herschrijven", type="primary"):
            rewrite_prompt = f"Ik wil graag de geconsolideerde content herschrijven voor de vraag: \"{active_project.vraag}\"."
            active_project.rewrite_messages = active_project.rewrite_messages + [{"role": "user", "content": rewrite_prompt}]
            st.rerun()
    
