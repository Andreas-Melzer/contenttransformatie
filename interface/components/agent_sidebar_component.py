import streamlit as st
from interface.project import Project

def display_agent_sidebar(project: Project, agent_name: str = "agent",doc_store=None):
    """
    Displays a generic agent sidebar component that can be used across different pages.

    Args:
        project: The current project
        agent_name: The name of the agent to use ('agent', 'consolidate_agent', or 'rewrite_agent')
    """
    # Get the appropriate agent and messages based on agent_name
    if agent_name == "agent":
        agent = project.agent
        messages = project.messages
        chat_placeholder = "Stel uw vraag..."
        title = "Zoek agent"
        description = "Stel hier vervolgvragen om relevante documenten te vinden."
    elif agent_name == "consolidate_agent":
        agent = project.consolidate_agent
        messages = project.consolidate_messages
        chat_placeholder = "Stel uw vraag over consolidatie..."
        title = "Consolidatie Agent"
        description = "Stel hier vragen over het consolidatieproces."
    elif agent_name == "rewrite_agent":
        agent = project.rewrite_agent
        messages = project.rewrite_messages
        chat_placeholder = "Stel uw vraag over herschrijven..."
        title = "Herschrijf Agent"
        description = "Stel hier vragen over het herschrijfproces."
    else:
        return

    with st.sidebar:
        st.title(title)
        st.write(description)
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
        if prompt := st.chat_input(chat_placeholder):
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

        # Process agent response if there's a user message
        if (agent and
            messages and
            messages[-1]["role"] == "user"):

            with st.chat_message("assistant"):
                with st.spinner("Agent is aan het werk..."):
                    agent.messages = messages
                    query = messages[-1]["content"]

                    # Call the appropriate chat method based on agent type
                    if agent_name == "agent":
                        final_response = agent.chat(
                            query=query,
                            hoofdvraag=project.vraag,
                            subvragen=project.subvragen,
                            max_tool_turns=15
                        )
                    elif agent_name == "consolidate_agent":
                        # Prepare selected documents for consolidation
                        docs = {}
                        for doc_id in project.saved_selection_consolidate:
                            #if doc_id in project.agent_found_documents or doc_id in project.self_found_documents:
                                docs[doc_id] = doc_store.documents[doc_id].content

                        final_response = agent.chat(
                            query=query,
                            hoofdvraag=project.vraag,
                            subvragen=project.subvragen,
                            geconsolideerde_tekst=project.consolidated_json,
                            selected_documents=docs,
                            max_tool_turns=15
                        )
                    elif agent_name == "rewrite_agent":
                        final_response = agent.chat(
                            query=query,
                            hoofdvraag=project.vraag,
                            subvragen=project.subvragen,
                            geconsolideerde_tekst=project.consolidated_json,
                            max_tool_turns=15
                        )

                    # Update project state
                    messages.extend(agent.messages[len(messages):])
                    st.rerun()