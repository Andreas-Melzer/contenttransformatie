from interface.project import Project
from interface.utils.project_manager import get_active_project
import streamlit as st

active_project: Project = get_active_project()
if not active_project:
    st.error("Selecteer alstublieft een project op het dashboard.")
    if st.button("Ga naar Dashboard"):
        st.switch_page("Project_Selectie.py")
    st.stop()
st.set_page_config(layout="wide")