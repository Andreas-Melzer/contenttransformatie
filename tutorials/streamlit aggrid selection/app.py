import streamlit as st
import pandas as pd
from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode, DataReturnMode

def create_aggrid_app():
    """
    Creates a Streamlit application to demonstrate AG Grid row selection.

    This function initializes a Streamlit app that displays a Pandas DataFrame
    in an AG Grid. When a user selects a row, the data for that row is
    logged to the console and displayed in the UI.
    """
    st.set_page_config(layout="wide")
    st.title("AG Grid Row Selection Tutorial")
    st.write(
        "This is a simple example of how to capture selected row data from an AG Grid "
        "table in a Streamlit application."
    )

    # --- 1. Create a Sample DataFrame ---
    # In a real application, you would load your data here.
    data = {
        'id': [1, 2, 3, 4, 5],
        'name': ['Alice', 'Bob', 'Charlie', 'David', 'Eve'],
        'age': [25, 30, 35, 40, 45],
        'city': ['New York', 'London', 'Paris', 'Tokyo', 'Sydney']
    }
    df = pd.DataFrame(data)

    st.subheader("Sample Data")
    st.dataframe(df)

    # --- 2. Configure AG Grid Options ---
    # We use GridOptionsBuilder to easily configure the grid's behavior.
    gb = GridOptionsBuilder.from_dataframe(df)

    # Configure row selection
    gb.configure_selection(
        'single',                   # Allow only single row selection
        use_checkbox=True,          # Show a checkbox column for selection
        groupSelectsChildren=True   # This is for grouped data, but good practice to include
    )

    # Build the grid options dictionary
    gridOptions = gb.build()

    # --- 3. Display the AG Grid Table ---
    st.subheader("Interactive AG Grid Table")
    st.info("Select a record by clicking the checkbox on the left.")

    grid_response = AgGrid(
        df,
        gridOptions=gridOptions,
        data_return_mode=DataReturnMode.FILTERED_AND_SORTED,
        # Update the grid when the selection changes
        update_mode=GridUpdateMode.MODEL_CHANGED,
        fit_columns_on_grid_load=True,
        allow_unsafe_jscode=True,
        enable_enterprise_modules=False,
        height=200,
        width='100%',
        key='selection_grid' # Added a key to help streamlit track the component's state
    )
    print(grid_response)
 
    # --- 4. Process and Display the Selected Data ---
    # The selected data is available in the 'selected_rows' key of the response.
    selected = grid_response['selected_rows']

    st.subheader("Selected Record Output")
    if selected is not None:
        # This will print the selected row to your server's console
        print("--- CONSOLE LOG ---")
        print("Selected Record:", selected)
        print("--------------------")

        st.write("You selected the following record:")
        # Convert the selected data (which is a list of dicts) to a DataFrame
        selected_df = pd.DataFrame(selected)
        # We can drop the '_selectedRowNodeId' column added by AG Grid
        selected_df.drop(columns=['_selectedRowNodeId'], inplace=True, errors='ignore')
        st.dataframe(selected_df)
    else:
        st.write("No record selected. Please select a row from the grid above.")
    #st.rerun()
if __name__ == "__main__":
    create_aggrid_app()
