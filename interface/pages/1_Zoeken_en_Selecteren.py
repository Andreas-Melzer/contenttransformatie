

from datetime import datetime as dt

import streamlit as st
import json
import pandas as pd
from typing import Dict
from interface.utils.global_store import global_store,AgentType
from interface.utils.project_manager import get_active_project
from interface.components.zelf_zoeken_component import display_zelf_zoeken
from interface.components.kme_document_grid import display_kme_document_grid_with_selector
from interface.components.kme_document_viewer import display_kme_document
from interface.project import Project
from interface.components.display_selections_ids import display_selection_ids
from interface.components.agent_sidebar_component import display_agent_sidebar
from interface.utils.timer import Timer
from interface.utils.global_store import global_store

def display_agent_search_results(project: Project, document_dict : Dict[str,int]):
    """Rendert de documententabel met AG Grid voor een interactieve ervaring."""
    col1, col2,_ =  st.columns([1, 1,1],gap="small",width=550)

    with Timer("Get Document grid data to display"):
        docs_data = []
        for doc_id, relevance in document_dict.items():
            doc = doc_store.documents.get(doc_id)
            if doc:
                meta = doc.metadata
                docs_data.append({
                    'km_nummer': doc_id,
                    'Belastingsoort': meta.get('BELASTINGSOORT', 'N/A'),
                    'Vraag': meta.get('VRAAG', 'N/A'),
                    'Proces': meta.get('PROCES_ONDERWERP', 'N/A'),
                    'Product': meta.get('PRODUCT_SUBONDERWERP', 'N/A'),
                    'Relevantie': relevance
                })

    if not docs_data:
        st.info("Er zijn geen documenten om")
        return

    with Timer("Create document grid dataframe"):
        df = pd.DataFrame(docs_data)
    with Timer("Display document grid"):
        display_kme_document_grid_with_selector(df, project, session_key="selected_docs", grid_key="agent_grid")

    with col1:
        if st.button(f"Selectie Opslaan ({len(st.session_state.selected_docs)})", type="primary",use_container_width=True):
            project.saved_selection_consolidate = st.session_state.selected_docs
            st.success(f"{len(st.session_state.selected_docs)} documenten opgeslagen voor de volgende stap.")
            st.rerun()

    with col2:
        if st.button(f"Verwijder Selectie ({len(st.session_state.selected_docs)})",use_container_width=True):
            for doc_id in st.session_state.selected_docs:
                if doc_id in project.agent_found_documents:
                    del project.agent_found_documents[doc_id]
                if doc_id in project.self_found_documents:
                    del project.self_found_documents[doc_id]
            st.session_state.selected_docs = []
            st.rerun()
    # geselecteerde documenten tonen
    st.subheader("Geselecteerde Documenten voor consolidatie")
    display_selection_ids(project.saved_selection_consolidate)
    



    
active_project =get_active_project()
st.set_page_config(layout="wide", page_title="Zoeken en selecteren")


with Timer("Load heavy compoenents"):
    _, doc_store, vector_store = global_store.get_heavy_components()
    
vector_store.metadata_filter = active_project.get_domain_filter()



if 'selected_doc_ids' not in st.session_state:
    st.session_state.selected_doc_ids = []
if 'aggrid_data' not in st.session_state:
    st.session_state.aggrid_data = None

with Timer("Display agent sidebar"):
    # Display agent sidebar
    display_agent_sidebar(active_project, agent_type="search")


with st.sidebar:
    if st.button("Start Automatisch Zoeken", type="primary"):
        search_prompt = f"Ik wil graag de geselecteerde documenten zoeken voor de vraag: \"{active_project.vraag}\" en eventuele subvragen {active_project.subvragen}."
        active_project.search_messages = active_project.search_messages + [{"role": "user", "content": search_prompt}]
        st.rerun()
        
st.title(f"Project: \"{active_project.vraag}\"")
st.header("Stap 1: Zoeken en Selecteren van Documenten")


tab1, tab2 = st.tabs(["Agent Zoeken", "Zelf Zoeken"])


with Timer("Display tabs"):
    with tab1:
        st.subheader("Gevonden Documenten")
        all_found_documents = {**active_project.agent_found_documents, **active_project.self_found_documents}
        if not all_found_documents:
            st.info("Er zijn nog geen documenten gevonden. Stel een vraag in de chat of gebruik 'Zelf zoeken' om te beginnen.")
        else:
            display_agent_search_results(active_project, all_found_documents)
            
        if active_project.selected_doc_id:
            display_kme_document(active_project, close_button_key="agent_close_doc")
    with tab2:
        display_zelf_zoeken()

