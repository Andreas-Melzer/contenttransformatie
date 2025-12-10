import uuid 
import pandas as pd
import streamlit as st
from contentcreatie.interface.styles.custom_css import apply_custom_css
from contentcreatie.interface.utils.project_manager import create_project, load_all_projects, load_project,force_delete_project
from contentcreatie.config.settings import settings
from logging import getLogger
from contentcreatie.config.paths import paths
from contentcreatie.log_config import LogBootstrap
LogBootstrap.load_config()
from contentcreatie.storage.storage_service import storage_service

KME_TABLE = pd.read_csv(paths.kme_vertaaltabel, sep=';')
print(paths.projects_folder)
logger = getLogger("Contenttransformatie")

logo_url = "https://www.belastingdienst.nl/bld-assets/bld/rhslogos/bld_logo.svg"

st.set_page_config(
    page_title="Content Creatie Dashboard",
    page_icon=logo_url,
    layout="wide",
)

apply_custom_css()

def initialize_session_state():
    """Initializes all necessary session state variables if they don't exist."""
    if "projects" not in st.session_state or st.session_state.projects is None:
        st.session_state.projects = load_all_projects()
    if "active_project_id" not in st.session_state:
        st.session_state.active_project_id = None
        
initialize_session_state() 

st.image(logo_url, width=500)
st.title("Content Projecten")

# --- NEW PROJECT FORM ---
st.header("Nieuw Project Starten")
with st.form("new_project_form"):
    project_question = st.text_area(
        "Wat is de vraag uit de nieuwe structuur die in dit document beantwoord wordt?"
    )

    project_subquestions = st.text_area(
        "Voer eventuele subvragen in (één per regel)",
        help="Voer hier één of meerdere subvragen in, gescheiden door een new line."
    )

    #FIXME magic string "ALLE BELASTINGSOORTEN" ergens anders configureren
    belastingsoort_options = ["ALLE BELASTINGSOORTEN"] + KME_TABLE.BELASTINGSOORT.unique().tolist()
    proces_options_list = KME_TABLE.PROCES_ONDERWERP.unique()
    product_options_list = KME_TABLE.PRODUCT_SUBONDERWERP.unique()

    belastingsoort = st.selectbox(
        "Selecteer Belastingsoort",
        options=belastingsoort_options,
        index=None,
        placeholder="Kies een belastingsoort..."
    )

    proces = st.selectbox(
        "Selecteer Proces",
        options=proces_options_list,
        index=None,
        placeholder="Kies een proces..."
    )

    product = st.selectbox(
        "Selecteer Product",
        options=product_options_list,
        index=None,
        placeholder="Kies een product..."
    )

    submitted = st.form_submit_button("Maak Nieuw Project")

    if submitted and project_question:
        project_id = str(uuid.uuid4())
        
        create_project(
            project_id=project_id, 
            vraag=project_question,
            subvragen=project_subquestions,
            belastingsoort=belastingsoort,
            proces=proces,
            product=product
        ) 
        
        st.success(f"Project '{project_question}' succesvol aangemaakt!")
        st.session_state.projects = load_all_projects() # Force reload list
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
            "project_id": None, # Hide ID
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
        # Handle filtering index mismatch
        selected_project_id = filtered_df.iloc[selected_row_index]['project_id']
        selected_question = filtered_df.iloc[selected_row_index]['vraag']

        st.divider()
        st.markdown(f"### Acties voor: *{selected_question}*")
        
        col1, col2, col3 = st.columns([1, 1, 4])
        
        with col1:
            if st.button("📂 Open Project", type="primary", use_container_width=True):
                st.session_state.active_project_id = selected_project_id
                st.switch_page("pages/1_Zoeken_en_Selecteren.py")

        with col2:
            if st.button("🔄 Reset", help="Wist alle voortgang, maar behoudt de vraag.", use_container_width=True):
                proj = load_project(selected_project_id)
                if proj:
                    proj.reset()
                    st.toast(f"Project '{selected_question}' is gereset naar beginstatus.")
                    # Optional: force a reload of metadata in case reset changed status
                    st.session_state.projects = load_all_projects()

        with col3:
            with st.popover("🗑️ Verwijderen", use_container_width=False):
                st.write("Weet je het zeker? Dit kan niet ongedaan worden gemaakt.")
                if st.button("Ja, verwijder definitief", type="primary"):
                    


                    force_delete_project(selected_project_id)
                    
                    st.success(f"Project verwijderd.")
                    
                    st.session_state.projects = load_all_projects()
                    st.rerun()