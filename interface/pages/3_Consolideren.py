import streamlit as st
from interface.utils.component_loader import load_heavy_components
from interface.utils.project_manager import get_active_project
from interface.utils.ui_components import display_document_dashboard

active_project = get_active_project()
st.set_page_config(layout="wide", page_title="Consolideren")