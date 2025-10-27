import streamlit as st
from interface.project import Project

def display_clear_agent_messages_button(project: Project, agent_name: str = "agent"):
    """
    Displays a button to clear agent messages and reset the agent.

    Args:
        project: The current project
        agent_name: The name of the agent to reset ('agent', 'consolidate_agent', or 'rewrite_agent')
    """
    if agent_name == "agent":
        agent = project.search_agent
        messages = project.search_messages
        label = "Clear Search Agent Messages"
    elif agent_name == "consolidate_agent":
        agent = project.consolidate_agent
        messages = project.consolidate_messages
        label = "Clear Consolidate Agent Messages"
    elif agent_name == "rewrite_agent":
        agent = project.rewrite_agent
        messages = project.rewrite_messages
        label = "Clear Rewrite Agent Messages"
    else:
        return

    if st.button(label, type="secondary"):
        # Clear messages
        messages.clear()
        project.save()
        if hasattr(agent, 'reset'):
            agent.reset()
        st.success(f"Messages cleared and {agent_name} reset!")
        st.rerun()