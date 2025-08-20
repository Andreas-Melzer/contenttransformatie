import streamlit as st
import pandas as pd
from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode, DataReturnMode, JsCode
from interface.utils.component_loader import load_components
from interface.utils.ui_components import display_document_viewer
from interface.utils.project_manager import get_active_project
from interface.utils.ui_components import display_document_table

# Pagina setup
st.set_page_config(layout="wide")

# Haal het actieve project op. Zonder actief project werkt deze pagina niet.
active_project = get_active_project()
if not active_project:
    st.error("Selecteer alstublieft een project op het dashboard.")
    if st.button("Ga naar Dashboard"):
        st.switch_page("app.py")
    st.stop()

# Laad de zware componenten (agent, doc_store)
agent, doc_store = load_components(active_project)

# Initialiseer session state voor selecties als die nog niet bestaat
if 'selected_doc_ids' not in st.session_state:
    st.session_state.selected_doc_ids = []
if 'aggrid_data' not in st.session_state:
    st.session_state.aggrid_data = None

# --- Sidebar met de chat ---
with st.sidebar:
    st.title("🤖 Onderzoeksagent")
    st.write("Stel hier vervolgvragen om relevante documenten te vinden.")
    st.divider()

    chat_container = st.container(height=300)
    with chat_container:
        for message in active_project["messages"]:
            if message["role"] == "user":
                with st.chat_message("user"):
                    st.markdown(message["content"])
            elif message["role"] == "assistant" and message.get("content"):
                with st.chat_message("assistant"):
                    st.markdown(message["content"])

    if prompt := st.chat_input("Stel uw vraag..."):
        active_project["messages"].append({"role": "user", "content": prompt})
        active_project["selected_doc_id"] = None
        # Reset selecties bij nieuwe vragen
        st.session_state.selected_doc_ids = []
        st.rerun()

    st.divider()
    with st.expander("Kladblok van de Agent"):
        scratchpad = active_project.get("scratchpad", [])
        if not scratchpad:
            st.caption("Het kladblok is leeg.")
        else:
            for task in scratchpad:
                completed = task.get('completed', False)
                task_text = task.get('task', 'N/A')
                st.markdown(f"✅ ~~{task_text}~~" if completed else f"☐ {task_text}")

# --- Hoofd content ---
st.title(f"Project: \"{active_project['vraag']}\"")
st.header("Stap 1: Zoeken en Selecteren van Documenten")
st.subheader("Gevonden Documenten")

if not active_project["shortlist"]:
    st.info("De agent heeft nog geen documenten gevonden. Stel een vraag in de chat om te beginnen.")
elif active_project.get("selected_doc_id"):
    display_document_viewer(doc_store, active_project)
else:
    display_document_table(doc_store, active_project)

# --- Agent logica ---
if active_project["messages"] and active_project["messages"][-1]["role"] == "user":
    with st.sidebar:
        with st.chat_message("assistant"):
            with st.spinner("Agent is aan het werk..."):
                agent.messages = active_project["messages"]
                agent.scratchpad = active_project["scratchpad"]
                query = active_project["messages"][-1]["content"]
                final_response = agent.chat(query=query, max_tool_turns=15)
                active_project["messages"].append({"role": "assistant", "content": final_response})
                active_project["scratchpad"] = agent.scratchpad
    # Reset selecties bij nieuwe berichten van de agent
    st.session_state.selected_doc_ids = []
    st.rerun()