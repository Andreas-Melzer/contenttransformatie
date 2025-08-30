import streamlit as st
import pandas as pd
from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode, DataReturnMode, JsCode
from typing import Dict, Any, List, Optional
from project import Project
from components.kme_document_viewer import display_kme_document
from components.kme_document_grid import display_kme_document_grid_with_selector
from pandas import DataFrame



def display_document_dashboard(doc_store, project: Project, document_dict : Dict[str,int]):
    """Rendert de documententabel met AG Grid voor een interactieve ervaring."""
    col1, col2, _ , _, _ = st.columns(5,vertical_alignment='top')
    
    docs_data = []
    for doc_id, relevance in document_dict.items():
        print
        doc = doc_store.documents.get(doc_id)
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

    if not docs_data:
        st.info("Er zijn geen documenten in de shortlist om weer te geven.")
        return

    df = pd.DataFrame(docs_data)
    display_kme_document_grid_with_selector(df, project, session_key="selected_docs")

    with col1:
        if st.button(f"Selectie Opslaan ({len(st.session_state.selected_docs)})", type="primary"):
            project.saved_selection_consolidate = st.session_state.selected_docs
            st.success(f"{len(st.session_state.selected_docs)} documenten opgeslagen voor de volgende stap.")
            st.rerun()
            
    with col2:
        if st.button(f"Verwijder Selectie ({len(st.session_state.selected_docs)})"):
            for doc_id in st.session_state.selected_docs:
                if doc_id in project.shortlist:
                    del project.shortlist[doc_id]
            st.session_state.selected_docs = []
            st.rerun()

    if project.selected_doc_id:
         display_kme_document(doc_store, project)

    st.subheader("Geselecteerde Documenten")
    st.write(project.saved_selection_consolidate)