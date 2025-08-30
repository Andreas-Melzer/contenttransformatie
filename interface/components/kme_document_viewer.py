from llm_client.document_vector_store import DocumentStore
from interface.project import Project
import streamlit as st

def display_kme_document(doc_store:DocumentStore, project: Project):
    """Rendert de detailweergave voor een geselecteerd document binnen een project."""
    if 'selected_docs' not in st.session_state:
        st.session_state.selected_docs = []
    st.divider()
    st.subheader("Document")
    doc = doc_store.documents.get(project.selected_doc_id,None)
    
    if not doc:
        st.warning(f"Document {project.selected_doc_id} niet gevonden in summary/raw store.")
    else:
        meta = getattr(doc, "metadata", {}) or {}
        st.markdown(f"### {getattr(doc, 'title', '')}")
        st.caption(getattr(doc, "id", ""))
        if meta.get('public_answer_html'):
            st.markdown(meta['public_answer_html'], unsafe_allow_html=True)
        if meta.get('private_answer_html'):
            st.markdown(
                f"""
                <div style="border-left: 4px solid red; padding: 8px 12px; margin: 10px 0; font-family: Arial, sans-serif;">
                    <div style="font-weight: bold; color: #c00; margin-bottom: 6px;">Privéantwoord 🔒</div>
                    <div>{meta['private_answer_html']}</div>
                </div>
                """,
                unsafe_allow_html=True
            )
        with st.expander("Samenvatting / content"):
            st.markdown(getattr(doc, "content", "") or "")
        if st.button("Sluit Document"):
            project.selected_doc_id = None
            st.session_state.zelfzoeken_just_closed_viewer = True
            st.rerun()