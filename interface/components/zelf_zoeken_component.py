# zelf_zoeken_component.py
# This module contains the Zelf Zoeken functionality as a reusable component

import json
import streamlit as st
import pandas as pd
from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode, DataReturnMode, JsCode
from interface.utils.project_manager import get_active_project
from interface.utils.component_loader import load_heavy_components
from interface.components.kme_document_viewer import display_kme_document
from interface.components.kme_document_grid import display_kme_document_grid_with_selector
from interface.project import Project

def display_zelf_zoeken():
    """
    Display the Zelf Zoeken interface as a component.
    This function contains all the logic from the original 2_Zelf_zoeken.py page.
    """
    active_project = get_active_project()
    st.set_page_config(layout="wide", page_title="Zelf zoeken")

    _, raw_doc_store, vector_store = load_heavy_components()

    # Initialize session state variables
    if "zelfzoeken_rows" not in st.session_state:
        st.session_state.zelfzoeken_rows = []
    if "zelfzoeken_mode" not in st.session_state:
        st.session_state.zelfzoeken_mode = "Vector search"
    if "zelfzoeken_selected" not in st.session_state:
        st.session_state.zelfzoeken_selected = []
    if "zelfzoeken_just_closed_viewer" not in st.session_state:
        st.session_state.zelfzoeken_just_closed_viewer = False
    if "zelfzoeken_last_click" not in st.session_state:
        st.session_state.zelfzoeken_last_click = None  # anti double-trigger

    def _mk_term(field: str, value: str, contains: bool = True) -> str:
        if not value:
            return ""
        v = value.strip().replace("\\", "\\\\").replace(":", "\\:").replace('"', '\\"')
        return f'{field}:*{v}*' if contains else f'{field}:{v}*'

    def build_taxonomy_query(belastingsoort: str, proces_onderwerp: str | None, product_subonderwerp: str | None, contains=True) -> str:
        parts = []
        if belastingsoort:
            parts.append(_mk_term("BELASTINGSOORT", belastingsoort, contains=contains))
        if proces_onderwerp:
            parts.append(_mk_term("PROCES_ONDERWERP", proces_onderwerp, contains=contains))
        if product_subonderwerp:
            parts.append(_mk_term("PRODUCT_SUBONDERWERP", product_subonderwerp, contains=contains))
        if not parts:
            return 'BELASTINGSOORT:*"*"'
        return " AND ".join([p for p in parts if p])

    def vector_search(vector_store, query: str, top_k: int = 10):
        """Probeer gangbare methoden op VectorStore (search/similarity_search/query)."""
        if not query:
            return []
        if hasattr(vector_store, "search"):
            try:
                return vector_store.search(query=query, k=top_k)
            except TypeError:
                try:
                    return vector_store.search(query, top_k)
                except Exception:
                    pass
            except Exception:
                pass
        if hasattr(vector_store, "similarity_search"):
            try:
                return vector_store.similarity_search(query, top_k)
            except Exception:
                pass
        if hasattr(vector_store, "query"):
            try:
                return vector_store.query(query, top_k)
            except Exception:
                pass
        st.warning("VectorStore mist een bekende zoekmethode (search/similarity_search/query). Pas de helper aan.")
        return []

    def _unwrap_hit(x):
        """
        Normaliseer mogelijke vector-hit vormen:
        - tuple: (doc, score) of (doc,)
        - dict: {"document": {...}, "score": 0.89} of {"id":..., "metadata":...}
        - object: met .document / .doc of direct doc-achtige attrs
        """
        doc, score = None, None
        if isinstance(x, tuple):
            doc = x[0] if len(x) > 0 else None
            score = x[1] if len(x) > 1 else None
        elif isinstance(x, dict):
            doc = x.get("document") or x.get("doc") or x.get("item") or x
            score = x.get("score") or x.get("similarity") or x.get("distance")
        else:
            # object-achtig
            doc = getattr(x, "document", None) or getattr(x, "doc", None) or x
            score = getattr(x, "score", None) or getattr(x, "similarity", None) or getattr(x, "distance", None)
        return doc, score

    def _get(doc, key, default=""):
        if doc is None:
            return default
        if isinstance(doc, dict):
            return doc.get(key, default)
        return getattr(doc, key, default)

    def docs_to_rows(docs):
        rows = []
        for hit in docs or []:
            doc, score = _unwrap_hit(hit)

            meta = _get(doc, "metadata", {}) or {}
            # Support dict & object
            km_id   = _get(doc, "id", "")
            title   = _get(doc, "title", "")
            content = _get(doc, "content", "") or ""
            snippet = (content[:220] + " ...") if content and len(content) > 220 else content

            rows.append({
                "km_nummer": km_id,
                "titel": title,
                "vraag": meta.get("VRAAG", ""),
                "belastingsoort": meta.get("BELASTINGSOORT", ""),
                "proces": meta.get("PROCES_ONDERWERP", ""),
                "product": meta.get("PRODUCT_SUBONDERWERP", ""),
                "score": score if score is not None else "",
                "snippet": snippet,
            })
        return rows

    def taxonomy_search(doc_store, belastingsoort: str, proces_onderwerp: str | None, product_subonderwerp: str | None, limit: int = 20, contains=True):
        q = build_taxonomy_query(belastingsoort, proces_onderwerp, product_subonderwerp, contains=contains)
        results = doc_store.search(query_string=q, limit=limit)
        # Handle case where results might be None or empty
        if results is None:
            results = []
        elif hasattr(results, 'empty') and results.empty:
            results = []
        return results, q

    st.title(f"Project: \"{active_project.vraag}\"")
    st.header("Zelf zoeken")

    with st.container():
        mode = st.radio("Zoektype", ["Vector search", "Taxonomie search"], horizontal=True, index=0 if st.session_state.zelfzoeken_mode=="Vector search" else 1)

        if mode == "Vector search":
            with st.form("vector_form", clear_on_submit=False):
                q = st.text_input("Zoekvraag (semantisch)", placeholder="bijv. ‘verliesverrekening box 1 na emigratie’")
                k = st.slider("Aantal resultaten", min_value=5, max_value=50, value=15, step=5)
                submitted = st.form_submit_button("Zoek")

            if submitted:
                with st.spinner("Zoeken in vector index..."):
                    results = vector_search(vector_store, q, top_k=k)
                rows = docs_to_rows(results)
                st.session_state.zelfzoeken_rows = rows
                st.session_state.zelfzoeken_mode = mode
                st.caption(f"Gevonden: {len(rows)}")
            else:
                rows = st.session_state.zelfzoeken_rows if st.session_state.zelfzoeken_mode == mode else []

        else:
            with st.form("taxonomy_form", clear_on_submit=False):
                colA, colB, colC = st.columns([1,1,1])
                with colA:
                    belastingsoort = st.text_input("BELASTINGSOORT (verplicht)", placeholder="bijv. IB - Inkomstenbelasting")
                with colB:
                    proces_onderwerp = st.text_input("PROCES_ONDERWERP (optioneel)", placeholder="bijv. Verliesverrekening")
                with colC:
                    product_subonderwerp = st.text_input("PRODUCT_SUBONDERWERP (optioneel)", placeholder="bijv. Verzoek verliesverrekening")
                c1, c2 = st.columns([1,3])
                with c1:
                    limit = st.number_input("Max resultaten", min_value=5, max_value=200, value=50, step=5)
                with c2:
                    contains_match = st.toggle("Bevat-match ( *term* ) i.p.v. prefix ( term* )", value=True)
                submitted = st.form_submit_button("Zoek")

            if submitted:
                if not (belastingsoort or "").strip():
                    st.error("BELASTINGSOORT is verplicht.")
                    rows = []
                else:
                    with st.spinner("Zoeken in metadata index..."):
                        results, q_str = taxonomy_search(
                            raw_doc_store,
                            belastingsoort=belastingsoort,
                            proces_onderwerp=proces_onderwerp or None,
                            product_subonderwerp=product_subonderwerp or None,
                            limit=int(limit),
                            contains=contains_match
                        )
                    rows = docs_to_rows(results)
                    st.session_state.zelfzoeken_rows = rows
                    st.session_state.zelfzoeken_mode = mode
                    st.caption(f"Query: `{q_str}`")
            else:
                rows = st.session_state.zelfzoeken_rows if st.session_state.zelfzoeken_mode == mode else []

    if rows:
        df = pd.DataFrame(rows)

        st.subheader("Resultaten")
        c1, c2, _ = st.columns([1,1,6], vertical_alignment='top')

        # Use the KME document grid component
        display_kme_document_grid_with_selector(df, active_project, session_key="zelfzoeken_selected_docs", grid_key="zelfzoeken_grid")

        with c1:
            if st.button(f"Voeg selectie toe ({len(st.session_state.zelfzoeken_selected_docs)})", type="primary", use_container_width=True):
                cnt = 0
                for doc_id in st.session_state.zelfzoeken_selected_docs:
                    if doc_id and doc_id not in active_project.self_found_documents:
                        active_project.self_found_documents[doc_id] = 0
                        cnt += 1
                st.success(f"{cnt} documenten toegevoegd aan selectie.")

        with c2:
            if st.button("Leeg selectie", use_container_width=True):
                st.session_state.zelfzoeken_selected_docs = []
                st.rerun()

        if getattr(active_project, "selected_doc_id", None):
            display_kme_document(raw_doc_store,active_project, close_button_key="zelfzoeken_close_doc")

    else:
        st.info("Nog geen resultaten. Voer een zoekopdracht uit.")