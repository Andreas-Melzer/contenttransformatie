import streamlit as st
import json
from interface.utils.component_loader import load_heavy_components
from interface.utils.project_manager import get_active_project
from llm_client.llm_client import json_decode
from interface.utils.consolidation_utils import format_consolidated_json
import pandas as pd
from interface.implementations.tools.save_consolidated_json_tool import SaveConsolidatedJsonTool
from interface.components.kme_document_grid import display_kme_document_grid_with_selector
from interface.components.clear_agent_messages import display_clear_agent_messages_button
from interface.components.agent_sidebar_component import display_agent_sidebar
                
active_project = get_active_project()
st.set_page_config(layout="wide", page_title="Consolideren")

# Load components
_, doc_store, vector_store = load_heavy_components()

# Display agent sidebar
display_agent_sidebar(active_project, agent_name="consolidate_agent",doc_store=doc_store)

# Initialize session state variables
if 'consolidate_selected_docs' not in st.session_state:
    st.session_state.consolidate_selected_docs = active_project.saved_selection_consolidate or []
    
if 'consolidated_text' not in st.session_state:
    st.session_state.consolidated_text = active_project.consolidated_text or {}
    
st.title(f"Project: \"{active_project.vraag}\"")
st.header("Stap 2: Consolideren van Documenten")

# Create tabs for different sections
tab1, tab2 = st.tabs(["Document Selectie", "Consolidatie Resultaat"])

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
                doc = doc_store.documents.get(doc_id)
                if doc:
                    meta = doc.metadata
                    docs_data.append({
                        'km_nummer': doc_id,
                        'Belastingsoort': meta.get('BELASTINGSOORT', 'N/A'),
                        'Vraag': meta.get('VRAAG', 'N/A'),
                        'Proces': meta.get('PROCES_ONDERWERP', 'N/A'),
                        'Product': meta.get('PRODUCT_SUBONDERWERP', 'N/A'),
                        'Relevante': relevance
                    })
            
            if docs_data:

                df = pd.DataFrame(docs_data)
                # Use a different session key to avoid conflicts
                display_kme_document_grid_with_selector(df, active_project, session_key="consolidate_selected_docs",selectable=False)


# Add button to clear agent messages in the sidebar
with st.sidebar:
    display_clear_agent_messages_button(active_project, "consolidate_agent")

    # Button to start automatic consolidation
    if st.button("Start Automatische Consolidatie", type="primary"):
        # Add a message to trigger consolidation
        consolidation_prompt = f"Ik wil graag de geselecteerde documenten consolideren voor de vraag: \"{active_project.vraag}\"."
        active_project.consolidate_messages = active_project.consolidate_messages + [{"role": "user", "content": consolidation_prompt}]
        st.rerun()

# Tab 3: Consolidation Result
with tab2:
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