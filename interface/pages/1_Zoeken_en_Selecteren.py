import streamlit as st
import json
from interface.utils.component_loader import load_heavy_components
from interface.utils.project_manager import get_active_project
from interface.utils.ui_components import display_agent_search_results
active_project =get_active_project()
st.set_page_config(layout="wide", page_title="Zoeken en selecteren")

_, doc_store, summary_doc_store, vector_store = load_heavy_components()

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
        # Re-assign the list to trigger the property setter
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
st.subheader("Gevonden Documenten")

# Combine agent and user found documents
all_found_documents = {**active_project.agent_found_documents, **active_project.self_found_documents}

if not all_found_documents:
    st.info("Er zijn nog geen documenten gevonden. Stel een vraag in de chat of gebruik 'Zelf zoeken' om te beginnen.")
else:
    display_agent_search_results(summary_doc_store, active_project, all_found_documents)

if agent and active_project.messages and active_project.messages[-1]["role"] == "user":
    with st.sidebar:
        with st.chat_message("assistant"):
            with st.spinner("Agent is aan het werk..."):
                # Synchroniseer de agent state met het project
                agent.messages = active_project.messages
                agent.scratchpad = active_project.scratchpad
                query = active_project.messages[-1]["content"]
                final_response = agent.chat(query=query, max_tool_turns=15)
                # Re-assign to save
                active_project.messages = agent.messages + [{"role": "assistant", "content": final_response}]
                # Synchroniseer terug
                active_project.scratchpad = agent.scratchpad
    st.session_state.selected_doc_ids = []
    st.rerun()