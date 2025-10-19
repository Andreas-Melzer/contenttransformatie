import streamlit as st
from interface.project import Project
from interface.utils.rewrite_utils import enrich_consolidation

AGENT_CONFIG = {
    "agent": {
        "agent_attr": "agent",
        "messages_attr": "messages",
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
    "consolidate_agent": {
        "agent_attr": "consolidate_agent",
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
    "rewrite_agent": {
        "agent_attr": "rewrite_agent",
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

def display_agent_sidebar(project: Project, agent_name: str = "agent", doc_store=None):
    """
    Displays a generic, data-driven agent sidebar component.

    :param project: Project, The current project
    :param agent_name: str, The name of the agent to use, defaults to 'agent'
    :param doc_store: Any, The document store object, defaults to None
    :return: None, This function does not return anything.
    """
    config = AGENT_CONFIG.get(agent_name)
    if not config:
        st.sidebar.error(f"Agent '{agent_name}' is not configured.")
        return

    agent = getattr(project, config["agent_attr"], None)
    messages = getattr(project, config["messages_attr"], [])

    with st.sidebar:
        st.title(config["title"])
        st.write(config["description"])
        st.divider()

        # Add a button to toggle chat visibility
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
            st.success(f"Messages cleared and {agent_name} reset!")
            st.rerun()