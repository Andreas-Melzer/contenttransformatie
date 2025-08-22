import streamlit as st
import pandas as pd
from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode, DataReturnMode, JsCode
from typing import Dict, Any, List, Optional

def display_document_viewer(doc_store, project: dict):
    """Rendert de detailweergave voor een geselecteerd document binnen een project."""
    doc_id = project.get("selected_doc_id")
    if not doc_id:
        return 

    with st.container(border=True):
        st.markdown('<div class="document-viewer">', unsafe_allow_html=True)
        doc = doc_store.documents.get(doc_id)

        if doc:
            st.header(doc.title)
            meta_html = " \n".join(
                f'<span class="metadata-chip"><strong>{key.replace("_", " ").title()}:</strong> {value}</span>'
                for key, value in doc.metadata.items() if value and key != 'full_text'
            )
            st.markdown(meta_html, unsafe_allow_html=True)
            st.divider()
            st.markdown(doc.content, unsafe_allow_html=True)
            if st.button("Sluit Document", key="close_doc"):
                project["selected_doc_id"] = None
        else:
            st.error(f"Document met ID {doc_id} niet gevonden.")
        st.markdown('</div>', unsafe_allow_html=True)

def display_document_dashboard(doc_store, project: dict):
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
        st.info("Er zijn geen documenten in de shortlist om weer te geven.")
        return

    df = pd.DataFrame(docs_data)
    df['double_clicked_id'] = ''


    onCellDoubleClicked = JsCode("""
        function(params) {
            const docId = params.data.id;
            const firstRowNode = params.api.getDisplayedRowAtIndex(0);
            if (firstRowNode) {
                firstRowNode.setDataValue('double_clicked_id', docId);
            }
        }
    """)

    gb = GridOptionsBuilder.from_dataframe(df)
    gb.configure_selection('multiple', use_checkbox=True, rowMultiSelectWithClick=True, suppressRowClickSelection=False)
    gb.configure_column("double_clicked_id", hide=True)
    gb.configure_grid_options(onCellDoubleClicked=onCellDoubleClicked)
    
    gridOptions = gb.build()

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
        editable=True,
        key='document_grid'
    )

    returned_df = grid_response['data']
    if returned_df is not None and not returned_df.empty:
        double_clicked_id = returned_df.iloc[0]['double_clicked_id']
        if double_clicked_id:
            project["selected_doc_id"] = double_clicked_id

    selected_rows = grid_response['selected_rows']
    if selected_rows is not None:
        selected_df = pd.DataFrame(selected_rows)
        if not selected_df.empty:
            st.session_state.selected_docs = selected_df['id'].tolist()
        else:
            st.session_state.selected_docs = []
    else:
        st.session_state.selected_docs = []

    # --- Action Buttons ---
    col1, col2, col3 , _, _ = st.columns(5)
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
    
    # documenten viewer
    if project.get("selected_doc_id"):
         display_document_viewer(doc_store, project)

    st.subheader("Geselecteerde Documenten")
    st.write(project.get('saved_selection_consolidate', []))