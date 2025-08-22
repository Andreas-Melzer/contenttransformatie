# Path: andreas-melzer/contentcreatie/Andreas-Melzer-contentcreatie-abf04f9d29ee9df5df0a2949b18f66d427f9aa2f/interface/utils/ui_components.py
import streamlit as st
import pandas as pd
from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode, DataReturnMode, JsCode
from typing import Dict, Any, List, Optional

def display_document_viewer(doc_store, project: dict):
    """Rendert de detailweergave voor een geselecteerd document binnen een project."""
    doc_id = project["selected_doc_id"]
    with st.container(border=True):
        st.markdown('<div class="document-viewer">', unsafe_allow_html=True)
        docs = doc_store.search(f"km_number:{doc_id}")
        doc = docs[0] if docs else None

        if doc:
            st.header(doc.title)
            meta_html = "".join(
                f'<span class="metadata-chip"><strong>{key.replace("_", " ").title()}:</strong> {value}</span>'
                for key, value in doc.metadata.items() if value and key != 'full_text'
            )
            st.markdown(meta_html, unsafe_allow_html=True)
            st.divider()
            st.markdown(doc.content, unsafe_allow_html=True)
            if st.button("Sluit Document", key="close_doc"):
                project["selected_doc_id"] = None
                st.rerun()
        else:
            st.error(f"Document met ID {doc_id} niet gevonden.")
        st.markdown('</div>', unsafe_allow_html=True)

def display_document_table(doc_store, project: dict):
    """Rendert de documententabel met AG Grid voor een interactieve ervaring."""
    if 'selected_docs' not in st.session_state:
        st.session_state.selected_docs = []

    docs_data = []
    for doc_id, shortlist_info in project["shortlist"].items():
        doc = doc_store.documents.get(doc_id)
        if doc:
            meta = doc.metadata
            docs_data.append({
                'id': doc_id,
                'km_nummer': meta.get('km_number', 'N/A'),
                'belastingsoort': meta.get('BELASTINGSOORT', 'N/A'),
                'vraag': meta.get('VRAAG', 'N/A'),
                'proces': meta.get('PROCES_ONDERWERP', 'N/A'),
                'product': meta.get('PRODUCT_SUBONDERWERP', 'N/A'),
                'relevantie': shortlist_info.get('relevance', '...')
            })

    if not docs_data:
        return

    df = pd.DataFrame(docs_data)

    # AG Grid configuratie
    gb = GridOptionsBuilder.from_dataframe(df)
    gb.configure_selection('multiple', use_checkbox=True, rowMultiSelectWithClick=True, suppressRowClickSelection=False)
    gb.configure_side_bar()
    gb.configure_grid_options(domLayout='normal')
    gridOptions = gb.build()

    # Toon de AG Grid tabel
    grid_response = AgGrid(
        df,
        gridOptions=gridOptions,
        height=600,
        width='100%',
        data_return_mode=DataReturnMode.AS_INPUT,
        update_mode=GridUpdateMode.MODEL_CHANGED,
        fit_columns_on_grid_load=False,
        allow_unsafe_jscode=True,
        enable_enterprise_modules=True,
        key='document_grid'
    )

    selected_rows = grid_response['selected_rows']

    # Handle selection processing safely to prevent TypeErrors
    if selected_rows is not None:
        selected_df = pd.DataFrame(selected_rows)
        if not selected_df.empty:
            st.session_state.selected_docs = selected_df['id'].tolist()
        else:
            st.session_state.selected_docs = []
    else:
        st.session_state.selected_docs = []

    # Actieknoppen
    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button(f"Selectie Opslaan ({len(st.session_state.selected_docs)})", type="primary"):
            project['saved_selection_consolidate'] = st.session_state.selected_docs
            st.success(f"{len(st.session_state.selected_docs)} documenten opgeslagen voor de volgende stap.")

    with col2:
        if st.button(f"Verwijder Selectie ({len(st.session_state.selected_docs)})"):
            for doc_id in st.session_state.selected_docs:
                if doc_id in project["shortlist"]:
                    del project["shortlist"][doc_id]
            st.session_state.selected_docs = []
            st.rerun()

    st.subheader("Geselecteerde Documenten")
    st.write(project['saved_selection_consolidate'])
