import uuid
import pandas as pd
import streamlit as st
from contentcreatie.interface.styles.custom_css import apply_custom_css
from contentcreatie.interface.utils.project_manager import create_project, load_all_projects, load_project, force_delete_project
from contentcreatie.config.settings import settings
from logging import getLogger
from contentcreatie.config.paths import paths
from contentcreatie.log_config import LogBootstrap
from contentcreatie.storage.storage_service import storage_service

# --- CONFIGURATION & SETUP ---
LogBootstrap.load_config()
KME_TABLE = pd.read_csv(paths.kme_vertaaltabel, sep=';')
logger = getLogger("Contenttransformatie")
apply_custom_css()

def project_to_row(project_id, data):
    """Normalizes dict or object data into a standard row format."""
    is_dict = isinstance(data, dict)
    get_val = lambda attr, key, default=None: data.get(key, default) if is_dict else getattr(data, attr, default)

    return {
        "project_id": project_id,
        "vraag": get_val("_vraag", "vraag", "N/A"),
        "belastingsoort": get_val("_belastingsoort", "belastingsoort", "N/A"),
        "proces_onderwerp": get_val("_proces_onderwerp", "proces_onderwerp", "N/A"),
        "product_subonderwerp": get_val("_product_subonderwerp", "product_subonderwerp", "N/A"),
        "datum_laatste_wijziging": get_val("_last_accesed_datetime", "last_accesed_datetime"),
        "archived": get_val("_archived", "archived", False)
    }

def initialize_session_state():
    """Initializes all necessary session state variables."""
    if "projects" not in st.session_state or st.session_state.projects is None:
        st.session_state.projects = load_all_projects()
    if "active_project_id" not in st.session_state:
        st.session_state.active_project_id = None
    if "logo_url" not in st.session_state:
        st.session_state.logo_url = "https://via.placeholder.com/150"

initialize_session_state() 

# --- DASHBOARD HEADER ---
col_logo, col_header, col_metric = st.columns([2, 2, 2], gap="medium")

with col_logo:
    st.image(st.session_state.logo_url, width=400)

with col_header:
    st.title("Content Projecten")
    st.caption("Beheer en start nieuwe content transformaties.")

with col_metric:
    all_projects = st.session_state.get("projects", {})
    active_count = sum(1 for p in all_projects.values() if not (isinstance(p, dict) and p.get('_archived') or getattr(p, '_archived', False)))
    st.metric(label="Actieve Projecten", value=active_count, delta=None)

st.divider()

# --- SECTION 1: CREATE NEW PROJECT ---
# Using icon code for the expander
with st.expander("Start een nieuw project", icon=":material/add_circle:", expanded=False):
    st.info("Vul de details in om een nieuwe analyse te starten.", icon=":material/info:")
    
    with st.form("new_project_form", border=False):
        col_input, col_meta = st.columns([2, 1], gap="large")
        
        with col_input:
            project_question = st.text_area(
                "Vraagstelling",
                placeholder="Wat is de vraag uit de nieuwe structuur...",
                height=150
            )
            project_subquestions = st.text_area(
                "Subvragen (optioneel)",
                placeholder="Eén subvraag per regel...",
                height=100
            )

        with col_meta:
            belastingsoort_options = ["ALLE BELASTINGSOORTEN"] + KME_TABLE['BELASTINGSOORT'].str.split('/', n=1).str[0].sort_values().unique().tolist()
            proces_options_list = KME_TABLE['PROCES_ONDERWERP'].str.split('/', n=1).str[0].sort_values().unique()
            product_options_list = KME_TABLE['PRODUCT_SUBONDERWERP'].str.split('/', n=1).str[0].sort_values().unique()

            belastingsoort = st.selectbox("Belastingsoort", options=belastingsoort_options, index=None)
            proces = st.selectbox("Proces", options=proces_options_list, index=None)
            product = st.selectbox("Product", options=product_options_list, index=None)

        st.markdown("<br>", unsafe_allow_html=True)
        col_submit, _ = st.columns([1, 4])
        with col_submit:
            # Using icon code for the submit button
            submitted = st.form_submit_button("Project Aanmaken", icon=":material/rocket_launch:", use_container_width=True)

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
            # Using icon code for the toast
            st.toast(f"Project aangemaakt!", icon=":material/check_circle:")
            st.session_state.projects = load_all_projects()
            st.rerun()

# --- SECTION 2: PROJECT OVERVIEW ---
st.subheader("Projecten Overzicht")

projects_metadata = st.session_state.get("projects", {})

if not projects_metadata:
    st.info("Er zijn nog geen projecten. Start hierboven een nieuw project.", icon=":material/info:")
else:
    project_list = [project_to_row(pid, d) for pid, d in projects_metadata.items()]
    df = pd.DataFrame(project_list)

    col_search, col_filter = st.columns([4, 2])
    
    with col_search:
        search_vraag = st.text_input(
            "Zoeken",
            placeholder="Zoek op project vraag...",
            label_visibility="collapsed"
        )
        # Note: text_input does not support an icon attribute, so we rely on the placeholder
    
    with col_filter:
        show_archived = st.toggle("Toon gearchiveerd", value=False)

    if search_vraag:
        df = df[df['vraag'].str.contains(search_vraag, case=False, na=False)]
    
    if not show_archived:
        filtered_df = df[df['archived'] == False]
    else:
        filtered_df = df

    st.dataframe(
        filtered_df,
        key='projects_grid',
        on_select="rerun",
        selection_mode="single-row",
        width="stretch",
        hide_index=True,
        column_config={
            "project_id": None, 
            "archived": None,
            "vraag": st.column_config.TextColumn("Vraagstelling", width="large"),
            "belastingsoort": st.column_config.TextColumn("Belastingsoort", width="small"),
            "proces_onderwerp": st.column_config.TextColumn("Proces", width="small"),
            "product_subonderwerp": st.column_config.TextColumn("Product", width="small"),
            "datum_laatste_wijziging": st.column_config.DatetimeColumn("Laatst gewijzigd", width="medium", format="D MMM YYYY, HH:mm")
        },
        height=400
    )

    selection = st.session_state.get('projects_grid')
    
    if selection and 'rows' in selection['selection'] and len(selection['selection']['rows']) > 0:
        selected_row_index = selection['selection']['rows'][0]
        selected_project_id = filtered_df.iloc[selected_row_index]['project_id']
        selected_question = filtered_df.iloc[selected_row_index]['vraag']

        with st.container(border=True):
            st.markdown(f"#### Acties voor geselecteerd project")
            st.caption(f"**Vraag:** {selected_question}")
            
            col_open, col_reset, col_archive, col_delete = st.columns([1, 1,1, 1], gap="small")
            
            with col_open:
                if st.button("Open Project", type="primary", icon=":material/folder_open:", use_container_width=True):
                    st.session_state.active_project_id = selected_project_id
                    st.switch_page("pages/1_Zoeken_en_Selecteren.py")

            with col_reset:
                if st.button("Reset", help="Wist alle voortgang.", icon=":material/refresh:", use_container_width=True):
                    proj = load_project(selected_project_id)
                    if proj:
                        proj.reset()
                        st.toast("Project is gereset.", icon=":material/refresh:")
                        st.session_state.projects = load_all_projects()
                        st.rerun()

            with col_archive:
                if st.button("Archiveer", help="Markeer dit project als gearchiveerd.", icon=":material/archive:", use_container_width=True):
                    proj = load_project(selected_project_id)
                    if proj:
                        proj.archived = True
                        st.toast("Project is gearchiveerd.", icon=":material/archive:")
                        st.session_state.projects = load_all_projects()
                        st.rerun()
                    
            with col_delete:
                with st.popover("Verwijder", icon=":material/delete:", use_container_width=True):
                    st.write("Definitief verwijderen?")
                    if st.button("Ja, verwijder", type="primary", use_container_width=True):
                        force_delete_project(selected_project_id)
                        st.toast("Project verwijderd.", icon=":material/delete:")
                        st.session_state.projects = load_all_projects()
                        st.rerun()