import streamlit as st
from interface.utils.component_loader import load_heavy_components
from interface.utils.project_manager import get_active_project
from llm_client.llm_client import json_decode
import json
from interface.implementations.tools.save_rewritten_json_tool import SaveRewrittenJsonTool

active_project = get_active_project()
st.set_page_config(layout="wide", page_title="Herschrijven")

# Load components
_, doc_store, vector_store = load_heavy_components()

st.title(f"Project: \"{active_project.vraag}\"")
st.header("Stap 4: Herschrijven van Geconsolideerde Content")

# Check if we have consolidated content
if not active_project.consolidated_json:
    st.info("Er is nog geen geconsolideerde content. Ga terug naar de consolidatie stap om content te consolideren.")
else:
    # Create tabs for different sections
    tab1, tab2, tab3 = st.tabs(["Geconsolideerde Content", "Herschrijf Agent", "Herschreven Content"])
    
    # Tab 1: Show consolidated content
    with tab1:
        st.subheader("Geconsolideerde Content")
        if active_project.consolidated_json:
            # Display consolidated content in a readable format
            consolidated_data = active_project.consolidated_json
            st.json(consolidated_data)
        else:
            st.info("Er is nog geen geconsolideerde content beschikbaar.")
    
    # Tab 2: Rewrite agent
    with tab2:
        st.subheader("Herschrijf Agent")
        
        # Display chat interface
        chat_container = st.container(height=400)
        with chat_container:
            for message in active_project.rewrite_messages:
                if message["role"] == "user":
                    with st.chat_message("user"):
                        st.markdown(message["content"])
                elif message["role"] == "assistant" and message.get("content"):
                    with st.chat_message("assistant"):
                        st.markdown(message["content"])
        
        # Chat input
        if prompt := st.chat_input("Stel uw vraag over herschrijven..."):
            # Add user message to history
            active_project.rewrite_messages = active_project.rewrite_messages + [{"role": "user", "content": prompt}]
            st.rerun()
        
        # Process agent response if there's a user message
        if (active_project.rewrite_agent and
            active_project.rewrite_messages and
            active_project.rewrite_messages[-1]["role"] == "user"):
            
            with st.chat_message("assistant"):
                with st.spinner("Herschrijf agent is aan het werk..."):
                    # Prepare the prompt with consolidated content
                    agent = active_project.rewrite_agent
                    agent.messages = active_project.rewrite_messages
                    query = active_project.rewrite_messages[-1]["content"]
                    
                    # Process the chat
                    final_response = agent.chat(
                        query=query,
                        max_tool_turns=15,
                        hoofdvraag = active_project.vraag,
                        subvragen = active_project.subvragen,
                        geconsolideerde_tekst = active_project.consolidated_json
                    )
                    
                    active_project.rewrite_messages = agent.messages
                    st.rerun()
        
        # Button to start automatic rewriting
        if st.button("Start Automatisch Herschrijven", type="primary"):
            # Add a message to trigger rewriting
            rewrite_prompt = f"Ik wil graag de geconsolideerde content herschrijven voor de vraag: \"{active_project.vraag}\"."
            active_project.rewrite_messages = active_project.rewrite_messages + [{"role": "user", "content": rewrite_prompt}]
            st.rerun()
    
    # Tab 3: Show rewritten content
    with tab3:
        st.subheader("Herschreven Content")
        if active_project.rewritten_text:
            st.markdown(active_project.rewritten_text)
        else:
            st.info("Er is nog geen herschreven content. Gebruik de herschrijf agent om content te genereren.")