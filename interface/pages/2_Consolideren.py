import streamlit as st
import json
from interface.utils.project_manager import get_active_project
from llm_client.llm_client import json_decode
from interface.utils.consolidation_utils import format_consolidated_json
import pandas as pd
from interface.implementations.tools.save_consolidated_json_tool import SaveConsolidatedJsonTool
from interface.components.kme_document_grid import display_kme_document_grid_with_selector
from interface.components.agent_sidebar_component import display_agent_sidebar
from interface.components.kme_document_viewer import display_kme_document
from interface.utils.global_store import global_store
                
active_project = get_active_project()
st.set_page_config(layout="wide", page_title="Consolideren")

if 'consolidate_selected_docs' not in st.session_state:
    st.session_state.consolidate_selected_docs = active_project.saved_selection_consolidate or []
    
if 'consolidated_text' not in st.session_state:
    st.session_state.consolidated_text = active_project.consolidated_text or {}
    
st.title(f"Project: \"{active_project.vraag}\"")
st.header("Stap 2: Consolideren van Documenten")

all_found_documents = {**active_project.agent_found_documents, **active_project.self_found_documents}
if not all_found_documents:
    st.info("Er zijn nog geen documenten gevonden. Ga terug naar de vorige stappen om documenten te vinden.")
else:
    tab1, tab2 = st.tabs(["Document Selectie", "Consolidatie Resultaat"])

    with tab1:
        st.subheader("Selecteer Documenten voor Consolidatie")
        selected_documents_with_relevance = {}
        for doc_id in active_project.saved_selection_consolidate:
            relevance = active_project.agent_found_documents.get(doc_id) or active_project.self_found_documents.get(doc_id, 0)
            selected_documents_with_relevance[doc_id] = relevance
        
        if not selected_documents_with_relevance:
            st.info("Er zijn nog geen documenten geselecteerd voor consolidatie. Ga naar de vorige stappen om documenten te selecteren.")
        else:
            docs_data = []
            for doc_id, relevance in selected_documents_with_relevance.items():
                doc = global_store.doc_store.documents.get(doc_id)
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
                display_kme_document_grid_with_selector(df, active_project, session_key="consolidate_selected_docs",selectable=False)

            # Display selected document if any
            if active_project.selected_doc_id:
                display_kme_document(active_project, close_button_key="consolidate_close_doc")
                
    display_agent_sidebar(active_project, agent_type="consolidate_agent")
    with st.sidebar:
        if st.button("Start Automatische Consolidatie", type="primary"):
            # Add a message to trigger consolidation
            consolidation_prompt = f"Ik wil graag de geselecteerde documenten consolideren voor de vraag: \"{active_project.vraag}\"."
            active_project.consolidate_messages = active_project.consolidate_messages + [{"role": "user", "content": consolidation_prompt}]
            st.rerun()

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