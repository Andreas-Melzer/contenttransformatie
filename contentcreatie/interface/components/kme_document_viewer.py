from project import Project
from utils.heavy_components import load_heavy_components
import streamlit as st
_,doc_store,_ = load_heavy_components()

def display_kme_document(project: Project, close_button_key="close_document"):
    """Renders a detailed view for a selected document in a styled container."""
    # Define the CSS for the document viewer card's internal elements.
    st.markdown("""
    <style>
    .doc-header {
        display: flex;
        align-items: center;
        justify-content: space-between;
        margin-bottom: 15px;
    }
    .doc-title {
        font-size: 5em;
        font-weight: 600;
        color: #0d3d6e; /* A dark blue for the title text */
        margin: 0;
    }
    .doc-id {
        background-color: #d6eaff; /* A light blue for the ID tag */
        color: #0d3d6e;
        padding: 4px 10px;
        border-radius: 15px;
        font-family: monospace;
        float: left;
        font-size: 0.9em;
    }
    .private-answer {
        border-left: 4px solid red;
        padding: 8px 12px;
        margin: 10px 0;
        background-color: #fff0f0;
    }
    .private-answer-header {
        font-weight: bold;
        color: #c00;
        margin-bottom: 6px;
    }
    </style>
    """, unsafe_allow_html=True)

    doc = doc_store.documents.get(project.selected_doc_id, None)
    if not doc:
        st.warning(f"Document {project.selected_doc_id} niet gevonden.")
        return

    # Use st.container(border=True) to correctly group all elements.
    with st.container(border=True,horizontal_alignment="left"):
        meta = getattr(doc, "metadata", {}) or {}

        # Styled Header (Title and ID)
        st.markdown(f"""
            <div class="doc-header">
                <p class="doc-title">{getattr(doc, 'title', '')}</p>
                <span class="doc-id">{getattr(doc, "id", "")}</span>
            </div>
        """, unsafe_allow_html=True)

        # Public Answer
        if meta.get('public_answer_html'):
            st.markdown(meta['public_answer_html'], unsafe_allow_html=True)

        # Private Answer
        if meta.get('private_answer_html'):
            st.markdown(f"""
                <div class="private-answer">
                    <div class="private-answer-header">Privéantwoord 🔒</div>
                    <div>{meta['private_answer_html']}</div>
                </div>
            """, unsafe_allow_html=True)
