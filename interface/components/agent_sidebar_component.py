import streamlit as st
from interface.project import Project
from interface.utils.rewrite_utils import enrich_consolidation
# Central configuration dictionary for all agent types
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
            #geconsolideerde_tekst=project.consolidated_json,
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

    # Dynamically get the agent and messages list from the project
    agent = getattr(project, config["agent_attr"], None)
    messages = getattr(project, config["messages_attr"], [])

    with st.sidebar:
        st.title(config["title"])
        st.write(config["description"])
        st.divider()

        # Display chat history
        chat_container = st.container(height=300)
        with chat_container:
            for message in messages:
                if message["role"] == "user":
                    with st.chat_message("user"):
                        st.markdown(message["content"])
                elif message["role"] == "assistant" and message.get("content"):
                    with st.chat_message("assistant"):
                        st.markdown(message["content"])

        # Chat input
        if prompt := st.chat_input(config["placeholder"]):
            # Note: .append() modifies in-place and won't trigger save by itself.
            # The agent response logic below handles the save via assignment.
            messages.append({"role": "user", "content": prompt})
            st.rerun()

        # Display scratchpad
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

        # Process agent response if the last message is from the user
        if agent and messages and messages[-1]["role"] == "user":
            with st.chat_message("assistant"):
                with st.spinner("Agent is aan het werk..."):
                    query = messages[-1]["content"]
                    
                    # Call the appropriate chat handler from the config
                    config["chat_handler"](agent, query, project, doc_store)
                    
                    # Assign the new message list back to trigger the setter and save()
                    setattr(project, config["messages_attr"], agent.messages)
                    st.rerun()

        if st.button("Clear messages", type="secondary"):
            # Assign an empty list to trigger the setter and its automatic save()
            setattr(project, config["messages_attr"], [])
            
            if hasattr(agent, 'reset'):
                agent.reset()
            
            st.success(f"Messages cleared and {agent_name} reset!")
            st.rerun()