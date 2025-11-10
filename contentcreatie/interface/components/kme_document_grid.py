import streamlit as st
import pandas as pd
from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode, DataReturnMode, JsCode
from project import Project
from pandas import DataFrame



def display_kme_document_grid_with_selector(df:DataFrame, project:Project, session_key="selected_docs", grid_key="document_grid",selectable=True):
    df['double_clicked_id'] = ''

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
    if selectable:
        gb.configure_selection('multiple', use_checkbox=True, rowMultiSelectWithClick=True, suppressRowClickSelection=False)
    else:
        gb.configure_selection('single', use_checkbox=False)
        
    gb.configure_column("double_clicked_id", hide=True)
    gb.configure_grid_options(onCellDoubleClicked=onCellDoubleClicked)

    gridOptions = gb.build()

    grid_response = AgGrid(
        df,
        gridOptions=gridOptions,
        height=600,
        width='100%',
        data_return_mode=DataReturnMode.FILTERED_AND_SORTED,
        update_mode=GridUpdateMode.MODEL_CHANGED,
        fit_columns_on_grid_load=False,
        show_toolbar=True,
        show_search=True,
        allow_unsafe_jscode=True,
        show_download_button=True,
        editable=True,
        key=grid_key
    )

    returned_df = grid_response['data']
    if not returned_df.empty:
        double_clicked_id = returned_df.iloc[0]['double_clicked_id']
        if double_clicked_id:
            print(f"clicked on {double_clicked_id} {returned_df.iloc[0]}")
            project.selected_doc_id = double_clicked_id

    selected_rows = grid_response['selected_rows']
    if selected_rows is not None:
        selected_df = pd.DataFrame(selected_rows)
        if not selected_df.empty:
            st.session_state[session_key] = selected_df['km_nummer'].tolist()
        else:
            st.session_state[session_key] = []
    else:
        st.session_state[session_key] = []
