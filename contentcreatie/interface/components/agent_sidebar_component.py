import streamlit as st
from project import Project
from utils.rewrite_utils import enrich_consolidation
from utils.heavy_components import load_heavy_components ,AgentType, get_agent
from logging import getLogger
logger = getLogger("Contenttransformatie")

_,doc_store,_ = load_heavy_components()


AGENT_CONFIG = {
    "search": {
        "messages_attr": "search_messages",
        "title": "Zoek agent",
        "description": "Stel hier vervolgvragen om relevante documenten te vinden.",
        "placeholder": "Stel uw vraag...",
        "chat_handler": lambda agent, query, project, doc_store: agent.chat(
            query=query,
            hoofdvraag=project.vraag,
            subvragen=project.subvragen,
            max_tool_turns=15
        )
    },
    "consolidate": {
        "messages_attr": "consolidate_messages",
        "title": "Consolidatie Agent",
        "description": "Stel hier vragen over het consolidatieproces.",
        "placeholder": "Stel uw vraag over consolidatie...",
        "chat_handler": lambda agent, query, project, doc_store: agent.chat(
            query=query,
            hoofdvraag=project.vraag,
            subvragen=project.subvragen,
            selected_documents={
                doc_id:  doc_store.documents[doc_id]
                for doc_id in project.saved_selection_consolidate
            },
            max_tool_turns=15
        )
    },
    "rewrite": {
        "messages_attr": "rewrite_messages",
        "title": "Herschrijf Agent",
        "description": "Stel hier vragen over het herschrijfproces.",
        "placeholder": "Stel uw vraag over herschrijven...",
        "chat_handler": lambda agent, query, project, doc_store: agent.chat(
            query=query,
            hoofdvraag=project.vraag,
            subvragen=project.subvragen,
            geconsolideerde_tekst= enrich_consolidation(project.consolidated_json,doc_store),
            herschreven_tekst = project.rewritten_text,
            max_tool_turns=15
        )
    }
}

def display_agent_sidebar(project: Project, agent_type: AgentType):
    """
    Displays a generic, data-driven agent sidebar component.

    :param project: Project, The current project
    :param agent_type: str, The name of the agent to use, defaults to 'agent'
    :param doc_store: Any, The document store object, defaults to None
    :return: None, This function does not return anything.
    """
    config = AGENT_CONFIG.get(agent_type)
    if not config:
        st.sidebar.error(f"Agent '{agent_type}' is not configured.")
        return

    agent = get_agent(project,agent_type)
    messages = getattr(project, config["messages_attr"], [])
    if not agent:
        logger.error("Unable to create agent")
        
    with st.sidebar:
        st.title(config["title"])
        st.write(config["description"])
        st.divider()

        if 'chat_visible' not in st.session_state:
            st.session_state.chat_visible = False

        if st.button("Toon chat" if not st.session_state.chat_visible else "Verberg chat"):
            st.session_state.chat_visible = not st.session_state.chat_visible
            st.rerun()

        if st.session_state.chat_visible:
            chat_container = st.container(height=300)
            with chat_container:
                for message in messages:
                    if message["role"] == "user":
                        with st.chat_message("user"):
                            st.markdown(message["content"])
                    elif message["role"] == "assistant" and message.get("content"):
                        with st.chat_message("assistant"):
                            st.markdown(message["content"])

            if prompt := st.chat_input(config["placeholder"]):
                messages.append({"role": "user", "content": prompt})
                st.rerun()

            st.divider()
            with st.expander("Kladblok van de Agent"):
                scratchpad = getattr(agent, 'scratchpad', []) if agent else []
                if not scratchpad:
                    st.caption("Het kladblok is leeg.")
                else:
                    for task in scratchpad:
                        completed = task.get('completed', False)
                        task_text = task.get('task', 'N/A')
                        st.markdown(f"✅ ~~{task_text}~~" if completed else f"☐ {task_text}")

            if agent and messages and messages[-1]["role"] == "user":
                with st.chat_message("assistant"):
                    with st.spinner("Agent is aan het werk..."):
                        query = messages[-1]["content"]
                        config["chat_handler"](agent, query, project, doc_store)
                        setattr(project, config["messages_attr"], agent.messages)
                        st.rerun()

        if st.button("Clear messages", type="secondary"):
            setattr(project, config["messages_attr"], [])
            if hasattr(agent, 'reset'):
                agent.reset()
            st.success(f"Messages cleared and {agent_type} reset!")
            st.rerun()