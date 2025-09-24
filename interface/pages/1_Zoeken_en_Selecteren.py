import streamlit as st
import json
import pandas as pd
from typing import Dict
from interface.utils.component_loader import load_heavy_components
from interface.utils.project_manager import get_active_project
from interface.components.zelf_zoeken_component import display_zelf_zoeken
from interface.components.kme_document_grid import display_kme_document_grid_with_selector
from interface.components.kme_document_viewer import display_kme_document
from interface.project import Project

def display_agent_search_results(doc_store, project: Project, document_dict : Dict[str,int]):
    """Rendert de documententabel met AG Grid voor een interactieve ervaring."""
    col1, col2,_ =  st.columns([1, 1,10])

    docs_data = []
    for doc_id, relevance in document_dict.items():
        doc = doc_store.documents.get(doc_id)
        if doc:
            meta = doc.metadata
            docs_data.append({
                'km_nummer': doc_id,
                'belastingsoort': meta.get('BELASTINGSOORT', 'N/A'),
                'vraag': meta.get('VRAAG', 'N/A'),
                'proces': meta.get('PROCES_ONDERWERP', 'N/A'),
                'product': meta.get('PRODUCT_SUBONDERWERP', 'N/A'),
                'relevantie': relevance
            })

    if not docs_data:
        st.info("Er zijn geen documenten in de shortlist om weer te geven.")
        return

    df = pd.DataFrame(docs_data)
    display_kme_document_grid_with_selector(df, project, session_key="selected_docs", grid_key="agent_grid")

    with col1:
        if st.button(f"Selectie Opslaan ({len(st.session_state.selected_docs)})", type="primary",use_container_width=True):
            project.saved_selection_consolidate = st.session_state.selected_docs
            st.success(f"{len(st.session_state.selected_docs)} documenten opgeslagen voor de volgende stap.")
            st.rerun()

    with col2:
        if st.button(f"Verwijder Selectie ({len(st.session_state.selected_docs)})",use_container_width=True):
            for doc_id in st.session_state.selected_docs:
                # Remove from both agent and self found documents
                if doc_id in project.agent_found_documents:
                    del project.agent_found_documents[doc_id]
                if doc_id in project.self_found_documents:
                    del project.self_found_documents[doc_id]
            st.session_state.selected_docs = []
            st.rerun()

    if project.selected_doc_id:
         display_kme_document(doc_store, project, close_button_key="agent_close_doc")

    st.subheader("Geselecteerde Documenten")
    st.write(project.saved_selection_consolidate)
active_project =get_active_project()
st.set_page_config(layout="wide", page_title="Zoeken en selecteren")

_, doc_store, vector_store = load_heavy_components()

agent = active_project.agent

def handle_list_documents(tool_call, project):
    """
    Callback function for the list_selected_documents tool.
    Returns the list of all selected documents (both agent-found and user-found).
    """
    # Get the function name and arguments
    function_name = tool_call['function']['name']
    args = json.loads(tool_call['function']['arguments'])

    # Get all selected documents
    all_documents = {
        "agent_found": list(project.agent_found_documents.keys()),
        "user_found": list(project.self_found_documents.keys())
    }

    # Return the result as a JSON string
    return json.dumps(all_documents)

if 'selected_doc_ids' not in st.session_state:
    st.session_state.selected_doc_ids = []
if 'aggrid_data' not in st.session_state:
    st.session_state.aggrid_data = None

with st.sidebar:
    st.title("Zoek agent")
    st.write("Stel hier vervolgvragen om relevante documenten te vinden.")
    st.divider()

    chat_container = st.container(height=300)
    with chat_container:
        for message in active_project.messages:
            if message["role"] == "user":
                with st.chat_message("user"):
                    st.markdown(message["content"])
            elif message["role"] == "assistant" and message.get("content"):
                with st.chat_message("assistant"):
                    st.markdown(message["content"])

    if prompt := st.chat_input("Stel uw vraag..."):
        active_project.messages = active_project.messages + [{"role": "user", "content": prompt}]
        active_project.selected_doc_id = None
        st.session_state.selected_doc_ids = []
        st.rerun()

    st.divider()
    with st.expander("Kladblok van de Agent"):
        scratchpad = active_project.scratchpad
        if not scratchpad:
            st.caption("Het kladblok is leeg.")
        else:
            for task in scratchpad:
                completed = task.get('completed', False)
                task_text = task.get('task', 'N/A')
                st.markdown(f"✅ ~~{task_text}~~" if completed else f"☐ {task_text}")

st.title(f"Project: \"{active_project.vraag}\"")
st.header("Stap 1: Zoeken en Selecteren van Documenten")

# Create tabs for different search methods
tab1, tab2 = st.tabs(["Agent Zoeken", "Zelf Zoeken"])

with tab1:
    st.subheader("Gevonden Documenten")

    all_found_documents = {**active_project.agent_found_documents, **active_project.self_found_documents}

    #documenten grid tonen
    if not all_found_documents:
        st.info("Er zijn nog geen documenten gevonden. Stel een vraag in de chat of gebruik 'Zelf zoeken' om te beginnen.")
    else:
        display_agent_search_results(doc_store, active_project, all_found_documents)

with tab2:
    # Display the Zelf Zoeken component
    display_zelf_zoeken()

if agent and active_project.messages and active_project.messages[-1]["role"] == "user":
    with st.sidebar:
        with st.chat_message("assistant"):
            with st.spinner("Agent is aan het werk..."):
                agent.messages = active_project.messages
                agent.scratchpad = active_project.scratchpad
                query = active_project.messages[-1]["content"]
                
                final_response = agent.chat(
                    query=query,
                    hoofdvraag = active_project.vraag ,
                    subvragen = active_project.subvragen,
                    max_tool_turns=15)
            
                active_project.messages = agent.messages
                active_project.scratchpad = agent.scratchpad
    st.session_state.selected_doc_ids = []
    st.rerun()