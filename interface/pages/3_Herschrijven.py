import streamlit as st
from interface.utils.component_loader import load_heavy_components
from interface.utils.project_manager import get_active_project
from interface.utils.ui_components import display_document_dashboard

# Pagina setup
st.set_page_config(layout="wide")

# Haal het actieve project op.
active_project = get_active_project()
if not active_project:
    st.error("Selecteer alstublieft een project op het dashboard.")
    if st.button("Ga naar Dashboard"):
        st.switch_page("Project_Selectie.py")
    st.stop()
