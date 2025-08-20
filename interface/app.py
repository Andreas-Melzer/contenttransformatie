import streamlit as st
import uuid
from interface.utils.project_manager import create_project, get_all_projects, initialize_projects
from interface.styles.custom_css import apply_custom_css

# Pagina Configuratie en Initialisatie
logo_url = "https://www.belastingdienst.nl/bld-assets/bld/rhslogos/bld_logo.svg"
st.set_page_config(
    page_title="Content Creatie Dashboard",
    page_icon=logo_url,
    layout="wide",
)
apply_custom_css()
initialize_projects()

st.image(logo_url, width=250)
st.title("Content Creatie Projecten")
st.markdown("Beheer hier uw contentgeneratie-projecten. Elk project start met een centrale vraag.")

# Nieuw Project Aanmaken
st.header("Nieuw Project Starten")
with st.form("new_project_form"):
    project_question = st.text_area(
        "Wat is de centrale vraag voor de nieuwe content?",
        placeholder="Bijvoorbeeld: Hoe werkt de belastingaangifte voor startende ondernemers?"
    )
    submitted = st.form_submit_button("Maak Nieuw Project")
    if submitted and project_question:
        project_id = str(uuid.uuid4())
        create_project(project_id, project_question)
        st.success(f"Project '{project_question}' succesvol aangemaakt!")
        # The st.rerun() here is removed. The page will update naturally.

# Bestaande Projecten Overzicht
st.header("Bestaande Projecten")
projects = get_all_projects()

if not projects:
    st.info("Er zijn nog geen projecten. Maak hierboven een nieuw project aan om te beginnen.")
else:
    for project_id, project_data in projects.items():
        with st.container(border=True):
            col1, col2 = st.columns([4, 1])
            with col1:
                st.subheader(project_data["vraag"])
                doc_count = len(project_data.get("shortlist", {}))
                st.caption(f"Geselecteerde documenten: {doc_count}")
            with col2:
                if st.button("Open Project", key=f"open_{project_id}", use_container_width=True):
                    st.session_state.active_project_id = project_id
                    st.switch_page("pages/1_Zoeken_en_Selecteren.py")