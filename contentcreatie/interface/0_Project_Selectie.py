

import uuid 
import pandas as pd
import streamlit as st
from contentcreatie.interface.styles.custom_css import apply_custom_css
from contentcreatie.interface.utils.project_manager import create_project, load_all_projects
import mlflow
from config.settings import settings
from config import mlflow_settings, get_logger

logger = get_logger()

logo_url = "https://www.belastingdienst.nl/bld-assets/bld/rhslogos/bld_logo.svg"

st.set_page_config(
    page_title="Content Creatie Dashboard",
    page_icon=logo_url,
    layout="wide",
)

apply_custom_css()
def initialize_session_state():
    """Initializes all necessary session state variables if they don't exist."""
    if "projects" not in st.session_state:
        st.session_state.projects = load_all_projects()
    if "active_project_id" not in st.session_state:
        st.session_state.active_project_id = None
        
initialize_session_state() # Centralized session state initialization

st.image(logo_url, width=500)
st.title("Content Projecten")

st.header("Nieuw Project Starten")
with st.form("new_project_form"):
    project_question = st.text_area(
        "Wat is de vraag uit de nieuwe structuur die in dit document beantwoord wordt?"
    )
    submitted = st.form_submit_button("Maak Nieuw Project")
    if submitted and project_question:
        project_id = str(uuid.uuid4())
        create_project(project_id, project_question)
        st.success(f"Project '{project_question}' succesvol aangemaakt!")
        st.session_state.projects = None
        st.rerun()

st.header("Bestaande Projecten")

projects_metadata = st.session_state.get("projects", {})
if not projects_metadata:
    st.info("Er zijn nog geen projecten. Maak hierboven een nieuw project aan om te beginnen.")
else:
    project_list = []
    for project_id, data in projects_metadata.items():
        vraag = ""
        if isinstance(data, dict):
            vraag = data.get("vraag", "Vraag niet gevonden")
            project_list.append({
            "project_id": project_id,
            "vraag": vraag,
            "belastingsoort": data.get("belastingsoort", "N/A"),
            "proces_onderwerp": data.get("proces_onderwerp", "N/A"),
            "product_subonderwerp": data.get("product_subonderwerp", "N/A"),
            })
        else:
            project_list.append({
            "project_id": project_id,
            "vraag":  getattr(data,"_vraag", "N/A"),
            "belastingsoort": getattr(data,"_belastingsoort", "N/A"),
            "proces_onderwerp": getattr(data,"_proces_onderwerp", "N/A"),
            "product_subonderwerp": getattr(data,"_product_subonderwerp", "N/A"),
            })

    df = pd.DataFrame(project_list)
    search_vraag = st.text_input("Zoek op project vraag:", placeholder="Typ hier om te zoeken...")
    if search_vraag:
        filtered_df = df[df['vraag'].str.contains(search_vraag, case=False, na=False)]
    else:
        filtered_df = df

    st.dataframe(
        filtered_df,
        key='projects_grid',
        on_select="rerun",
        selection_mode="single-row",
        use_container_width=True,
        hide_index=True,
        column_config={
            "project_id": None,
            "vraag": st.column_config.TextColumn("Vraag", width="large"),
            "belastingsoort": st.column_config.TextColumn("Belastingsoort", width="medium"),
            "proces_onderwerp": st.column_config.TextColumn("Proces Onderwerp", width="medium"),
            "product_subonderwerp": st.column_config.TextColumn("Product Subonderwerp", width="medium"),
        },
        height=400
    )


    selection = st.session_state.get('projects_grid')
    if selection and 'rows' in selection['selection'] and len(selection['selection']['rows']) > 0:
        selected_row_index = selection['selection']['rows'][0]
        selected_project_id = filtered_df.iloc[selected_row_index]['project_id']
        st.session_state.active_project_id = selected_project_id
        st.switch_page("pages/1_Zoeken_en_Selecteren.py")