import streamlit as st
st.session_state.logo_url = "https://www.belastingdienst.nl/bld-assets/bld/rhslogos/bld_logo.svg"
st.set_page_config(
    page_title="Content Creatie Dashboard",
    page_icon=st.session_state.logo_url,
    layout="wide",
)

from utils.heavy_components import load_heavy_components
with st.spinner("Systeem initialiseren (FAISS & LLM)..."):
    load_heavy_components()
from utils.auth_check import require_access
user = require_access()

if user:
    st.session_state.user = user
    pg = st.navigation([
        st.Page("pages/0_Project_Selectie.py", title="Project Selectie", icon="📁", default=True),
        st.Page("pages/1_Zoeken_en_Selecteren.py", title="Zoeken & Selecteren", icon="🔍"),
        st.Page("pages/2_Consolideren.py", title="Consolideren", icon="🧠"),
        st.Page("pages/3_Herschrijven.py", title="Herschrijven", icon="✍️"),
    ])
    
    pg.run()
else:
    st.warning("U heeft geen toegang tot deze applicatie.")