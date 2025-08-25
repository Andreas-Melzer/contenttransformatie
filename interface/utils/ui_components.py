import streamlit as st
import pandas as pd
from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode, DataReturnMode, JsCode
from typing import Dict, Any, List, Optional
# Forward declaration for type hinting
class Project:
    pass

def display_document_viewer(doc_store, project: "Project"):
    """Rendert de detailweergave voor een geselecteerd document binnen een project."""
    doc_id = project.selected_doc_id
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
                project.selected_doc_id = None
                st.session_state['just_closed_viewer'] = True  # Set a flag to ignore grid state
                st.rerun()
        else:
            st.error(f"Document met ID {doc_id} niet gevonden.")
        st.markdown('</div>', unsafe_allow_html=True)

def display_document_dashboard(doc_store, project: "Project"):
    """Rendert de documententabel met AG Grid voor een interactieve ervaring."""
    # Pop the flag at the beginning. It will be True if the viewer was just closed.
    viewer_was_closed = st.session_state.pop('just_closed_viewer', False)

    if 'selected_docs' not in st.session_state:
        st.session_state.selected_docs = []

    docs_data = []
    for doc_id, shortlist_info in project.shortlist.items():
        doc = doc_store.documents.get(doc_id)
        if doc:
            meta = doc.metadata
            docs_data.append({
                'km_nummer': doc_id,
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

    col1, col2, col3 , _, _ = st.columns(5,vertical_alignment='top')
    onCellDoubleClicked = JsCode("""
        function(params) {
            const docId = params.data.km_nummer;
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
        show_download_button=True,
        editable=True,
        key='document_grid'
    )

    returned_df = grid_response['data']
    # Only process the double-click if the viewer wasn't just closed.
    if not viewer_was_closed and returned_df is not None and not returned_df.empty:
        double_clicked_id = returned_df.iloc[0]['double_clicked_id']
        if double_clicked_id:
            project.selected_doc_id = double_clicked_id

    selected_rows = grid_response['selected_rows']
    if selected_rows is not None:
        selected_df = pd.DataFrame(selected_rows)
        if not selected_df.empty:
            st.session_state.selected_docs = selected_df['km_nummer'].tolist()
        else:
            st.session_state.selected_docs = []
    else:
        st.session_state.selected_docs = []


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

    # documenten viewer
    if project.selected_doc_id:
         display_document_viewer(doc_store, project)

    st.subheader("Geselecteerde Documenten")
    st.write(project.saved_selection_consolidate)