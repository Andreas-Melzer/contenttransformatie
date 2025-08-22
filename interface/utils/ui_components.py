import streamlit as st
import pandas as pd
from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode, DataReturnMode
from typing import Dict, Any, List, Optional

def display_document_viewer(doc_store, project: dict):
    """Rendert de detailweergave voor een geselecteerd document binnen een project."""
    doc_id = project["selected_doc_id"]
    with st.container(border=True):
        st.markdown('<div class="document-viewer">', unsafe_allow_html=True)
        docs = doc_store.search(f"km_number:{doc_id}")
        doc = docs[0] if docs else None

        if doc:
            st.header(doc.title)
            meta_html = "".join(
                f'<span class="metadata-chip"><strong>{key.replace("_", " ").title()}:</strong> {value}</span>'
                for key, value in doc.metadata.items() if value and key != 'full_text'
            )
            st.markdown(meta_html, unsafe_allow_html=True)
            st.divider()
            st.markdown(doc.content, unsafe_allow_html=True)
            if st.button("Sluit Document", key="close_doc"):
                project["selected_doc_id"] = None
                st.rerun()
        else:
            st.error(f"Document met ID {doc_id} niet gevonden.")
        st.markdown('</div>', unsafe_allow_html=True)

def display_document_table(doc_store, project: dict):
    """Versie met directe state updates en bredere layout."""
    
    if 'selected_docs' not in st.session_state:
        st.session_state.selected_docs = set()
    
    docs_list = []
    for doc_id, shortlist_info in project["shortlist"].items():
        doc = doc_store.documents[doc_id]
        docs_list.append({
            'id': doc_id,
            'doc': doc,
            'relevance': shortlist_info.get('relevance')
        })

    # Sorteer op relevantie
    def get_relevance_score(item):
        try:
            relevance = item.get('relevance')
            if relevance and relevance != '...':
                return float(relevance)
        except (ValueError, TypeError):
            pass
        return -1
    
    docs_list.sort(key=get_relevance_score, reverse=True)
    
    # --- Control Panel bovenaan ---
    with st.container(border=True):
        col1, col2, col3, col4, col5 = st.columns([2, 2, 2, 1, 1])
        
        with col1:
            subcol1, subcol2 = st.columns(2)
            with subcol1:
                if st.button("✓ Alle", use_container_width=True, help="Selecteer alle documenten"):
                    st.session_state.selected_docs = {d['id'] for d in docs_list}
                    st.rerun()
            with subcol2:
                if st.button("✗ Geen", use_container_width=True, help="Deselecteer alle documenten"):
                    st.session_state.selected_docs = set()
                    st.rerun()
        
        with col2:
            delete_disabled = len(st.session_state.selected_docs) == 0
            if st.button(f"🗑️ Verwijder selectie ({len(st.session_state.selected_docs)})", 
                        use_container_width=True,
                        disabled=delete_disabled):
                for doc_id in list(st.session_state.selected_docs):
                    if doc_id in project["shortlist"]:
                        del project["shortlist"][doc_id]
                st.session_state.selected_docs = set()
                st.rerun()
        
        with col3:
            save_disabled = len(st.session_state.selected_docs) == 0
            if st.button(f"💾 Bewaar voor volgende stap ({len(st.session_state.selected_docs)})", 
                        use_container_width=True,
                        type="primary",
                        disabled=save_disabled):
                for doc_id in project["shortlist"]:
                    project["shortlist"][doc_id]['saved_for_next_step'] = doc_id in st.session_state.selected_docs
                st.success(f"✓ {len(st.session_state.selected_docs)} document(en) opgeslagen")
        
        with col4:
            st.metric("Totaal", len(docs_list))
        
        with col5:
            st.metric("Selectie", len(st.session_state.selected_docs))
    
    # --- Document lijst met inline viewers ---
    for item in docs_list:
        doc = item['doc']
        doc_id = item['id']
        meta = doc.metadata
        relevance = item.get('relevance', '...')
        if relevance is None:
            relevance = '...'
        
        with st.container(border=True):
            # Gebruik on_change callback voor directe updates
            def toggle_selection(doc_id=doc_id):
                if doc_id in st.session_state.selected_docs:
                    st.session_state.selected_docs.remove(doc_id)
                else:
                    st.session_state.selected_docs.add(doc_id)
            
            # Header row
            col1, col2, col3, col4, col5 = st.columns([0.5, 2, 10, 2, 1])
            
            with col1:
                # Checkbox met directe callback
                st.checkbox(
                    label="Select",
                    value=doc_id in st.session_state.selected_docs,
                    key=f"check_{doc_id}",
                    label_visibility="collapsed",
                    on_change=toggle_selection
                )
            
            with col2:
                st.markdown(f"**{meta.get('km_number', 'N/A')}**")
            
            with col3:
                vraag = meta.get('VRAAG', 'N/A')
                st.write(vraag[:200] + "..." if len(vraag) > 200 else vraag)
            
            with col4:
                st.caption(f"{meta.get('BELASTINGSOORT', 'N/A')}")
                st.caption(f"{meta.get('PROCES_ONDERWERP', 'N/A')}")
            
            with col5:
                if relevance != '...':
                    try:
                        score = float(relevance)
                        color = "🟢" if score > 7 else "🟡" if score > 4 else "🔴"
                        st.markdown(f"{color} **{relevance}**")
                    except:
                        st.markdown(f"**{relevance}**")
                else:
                    st.markdown("⚪ **...**")
            
            # Expandable detail sectie - volle breedte
            with st.expander("📄 **Bekijk volledig antwoord**", expanded=False):
                # Info header
                infocol1, infocol2, infocol3 = st.columns(3)
                with infocol1:
                    st.markdown(f"**KM Nummer:** {meta.get('km_number', 'N/A')}")
                with infocol2:
                    st.markdown(f"**Product:** {meta.get('PRODUCT_SUBONDERWERP', 'N/A')}")
                with infocol3:
                    st.markdown(f"**Relevantie Score:** {relevance}")
                
                st.divider()
                
                # Vraag
                st.markdown("### Vraag")
                st.info(meta.get('VRAAG', 'N/A'))
                
                # Antwoord - met scrollbare container voor lange teksten
                st.markdown("### Antwoord")
                with st.container(height=400):
                    st.markdown(doc.content)
                
                # Acties voor dit specifieke document
                st.divider()
                actcol1, actcol2, actcol3 = st.columns(3)
                with actcol1:
                    if st.button(f"🗑️ Verwijder dit document", key=f"del_{doc_id}", use_container_width=True):
                        if doc_id in project["shortlist"]:
                            del project["shortlist"][doc_id]
                        if doc_id in st.session_state.selected_docs:
                            st.session_state.selected_docs.remove(doc_id)
                        st.rerun()
                with actcol2:
                    if st.button(f"💾 Bewaar alleen dit document", key=f"save_{doc_id}", use_container_width=True):
                        for did in project["shortlist"]:
                            project["shortlist"][did]['saved_for_next_step'] = (did == doc_id)
                        st.success(f"Document {meta.get('km_number', 'N/A')} opgeslagen")
                with actcol3:
                    if st.button(f"📋 Kopieer antwoord", key=f"copy_{doc_id}", use_container_width=True):
                        st.code(doc.content, language=None)