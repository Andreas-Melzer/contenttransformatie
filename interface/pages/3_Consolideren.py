import streamlit as st
import json
from interface.utils.component_loader import load_heavy_components
from interface.utils.project_manager import get_active_project
from interface.components.ui_components import display_agent_search_results
from llm_client.llm_client import json_decode
from interface.utils.consolidation_utils import format_consolidated_json
import pandas as pd
from interface.components.kme_document_grid import display_kme_document_grid_with_selector
                
active_project = get_active_project()
st.set_page_config(layout="wide", page_title="Consolideren")

# Load components
_, doc_store, summary_doc_store, vector_store = load_heavy_components()

# Initialize session state variables
if 'consolidate_selected_docs' not in st.session_state:
    st.session_state.consolidate_selected_docs = active_project.saved_selection_consolidate or []
    
if 'consolidated_text' not in st.session_state:
    st.session_state.consolidated_text = active_project.consolidated_text or {}
    
st.title(f"Project: \"{active_project.vraag}\"")
st.header("Stap 3: Consolideren van Documenten")

# Create tabs for different sections
tab1, tab2, tab3 = st.tabs(["Document Selectie", "Consolidatie Agent", "Consolidatie Resultaat"])

# Tab 1: Document Selection
with tab1:
    st.subheader("Selecteer Documenten voor Consolidatie")
    
    # Combine agent and user found documents
    all_found_documents = {**active_project.agent_found_documents, **active_project.self_found_documents}
    
    if not all_found_documents:
        st.info("Er zijn nog geen documenten gevonden. Ga terug naar de vorige stappen om documenten te vinden.")
    else:
        # Create a dictionary with document IDs and their relevance scores for selected documents
        selected_documents_with_relevance = {}
        for doc_id in active_project.saved_selection_consolidate:
            # Get relevance from either agent_found or self_found documents
            relevance = active_project.agent_found_documents.get(doc_id) or active_project.self_found_documents.get(doc_id, 0)
            selected_documents_with_relevance[doc_id] = relevance
        
        if not selected_documents_with_relevance:
            st.info("Er zijn nog geen documenten geselecteerd voor consolidatie. Ga naar de vorige stappen om documenten te selecteren.")
        else:
            # Display selected documents in a table
            docs_data = []
            for doc_id, relevance in selected_documents_with_relevance.items():
                doc = summary_doc_store.documents.get(doc_id)
                if doc:
                    meta = doc.metadata
                    docs_data.append({
                        'km_nummer': doc_id,
                        'belastingsoort': meta.get('BELASTINGSOORT', 'N/A'),
                        'vraag': meta.get('VRAAG', 'N/A'),
                        'proces': meta.get('PROCES_ONDERWERP', 'N/A'),
                        'product': meta.get('PRODUCT_SUBONDERWERP', 'N/A'),
                        'relevantie': relevance
                    })
            
            if docs_data:

                df = pd.DataFrame(docs_data)
                # Use a different session key to avoid conflicts
                display_kme_document_grid_with_selector(df, active_project, session_key="consolidate_selected_docs")
                
                st.subheader("Geselecteerde Documenten voor Consolidatie")
                st.write(f"Aantal geselecteerde documenten: {len(st.session_state.consolidate_selected_docs)}")
                
                # Button to update the saved selection
                if st.button("Update Selectie", type="primary"):
                    active_project.saved_selection_consolidate = st.session_state.consolidate_selected_docs
                    st.success("Selectie bijgewerkt!")
                    st.rerun()

# Tab 2: Consolidation Agent
with tab2:
    st.subheader("Consolidatie Agent")
    
    # Check if we have selected documents
    if not st.session_state.consolidate_selected_docs:
        st.info("Selecteer eerst documenten in de 'Document Selectie' tab.")
    else:
        # Create a dictionary with document IDs and their relevance scores
        selected_documents_with_relevance = {}
        for doc_id in st.session_state.consolidate_selected_docs:
            # Get relevance from either agent_found or self_found documents
            relevance = active_project.agent_found_documents.get(doc_id) or active_project.self_found_documents.get(doc_id, 0)
            selected_documents_with_relevance[doc_id] = relevance
        
        # Display chat interface
        chat_container = st.container(height=400)
        with chat_container:
            for message in active_project.consolidate_messages:
                if message["role"] == "user":
                    with st.chat_message("user"):
                        st.markdown(message["content"])
                elif message["role"] == "assistant" and message.get("content"):
                    with st.chat_message("assistant"):
                        st.markdown(message["content"])
        
        # Display scratchpad
        with st.expander("Kladblok van de Consolidatie Agent"):
            scratchpad = active_project.consolidate_agent.scratchpad if active_project.consolidate_agent else []
            if not scratchpad:
                st.caption("Het kladblok is leeg.")
            else:
                for task in scratchpad:
                    completed = task.get('completed', False)
                    task_text = task.get('task', 'N/A')
                    st.markdown(f"✅ ~~{task_text}~~" if completed else f"☐ {task_text}")
        
        # Chat input
        if prompt := st.chat_input("Stel uw vraag over consolidatie..."):
            # Add user message to history
            active_project.consolidate_messages = active_project.consolidate_messages + [{"role": "user", "content": prompt}]
            st.rerun()
        
        # Process agent response if there's a user message
        if (active_project.consolidate_agent and
            active_project.consolidate_messages and
            active_project.consolidate_messages[-1]["role"] == "user"):
            
            with st.chat_message("assistant"):
                with st.spinner("Consolidatie agent is aan het werk..."):
                    # Prepare the prompt with selected documents
                    agent = active_project.consolidate_agent
                    agent.messages = active_project.consolidate_messages
                    query = active_project.consolidate_messages[-1]["content"]
                    
                    docs = {}
                    for id, score in selected_documents_with_relevance.items():
                        docs[id] = doc_store.documents[id].content
                        
                    # Process the chat
                    final_response = agent.chat(
                        query=query,
                        max_tool_turns=15,
                        hoofdvraag = active_project.vraag ,
                        subvragen = active_project.subvragen,
                        geconsolideerde_tekst = active_project.consolidated_text,
                        selected_documents=docs
                    )
                    
                    #TODO dit moet met tools gedaan worden nu lelijke oplossing
                    final_response_json = json_decode(final_response)
                    
                    if final_response_json:
                        active_project.consolidate_messages.append({"role":"assistant","content" : final_response_json['bericht']})
                        active_project.consolidated_json = final_response_json
                    st.rerun()
        
        # Button to start automatic consolidation
        if st.button("Start Automatische Consolidatie", type="primary"):
            # Add a message to trigger consolidation
            consolidation_prompt = f"Ik wil graag de geselecteerde documenten consolideren voor de vraag: \"{active_project.vraag}\"."
            active_project.consolidate_messages = active_project.consolidate_messages + [{"role": "user", "content": consolidation_prompt}]
            st.rerun()

# Tab 3: Consolidation Result
with tab3:
    # Display consolidated text as Markdown
    st.markdown("### Geconsolideerde Tekst")
    consolidated_markdown = format_consolidated_json(active_project.consolidated_json)
    st.markdown(consolidated_markdown)
    
        
    # Load from agent button (if there's content in the last assistant message)
    if (active_project.consolidate_messages and
        active_project.consolidate_messages[-1]["role"] == "assistant" and
        active_project.consolidate_messages[-1].get("content")):
        if st.button("Laad laatste agent output"):

            agent_output = active_project.consolidate_messages[-1]["content"]
            try:
                agent_json = json.loads(agent_output)
                st.session_state.consolidated_text = format_consolidated_json(agent_json)
            except json.JSONDecodeError:
                st.session_state.consolidated_text = agent_output
            st.rerun()