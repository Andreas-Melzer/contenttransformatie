import streamlit as st
from typing import List

def display_selection_ids(selection: List[str]):
    """Renders a list of strings as styled, selectable tags.

    :param selection: List[str], The list of items to display as tags.
    :return: None, This function renders components directly to the Streamlit app.
    """
    st.markdown("""
    <style>
        .tag-container {
            display: flex;
            flex-wrap: wrap;
            gap: 8px; /* Space between tags */
            margin-top: 10px;
        }
        .tag {
            display: inline-block;
            padding: 6px 12px;
            margin-bottom: 8px; /* Space below tags if they wrap */
            border-radius: 16px;
            background-color: #f0f2f6;
            color: #31333f;
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
            font-size: 0.9rem;
            font-weight: 500;
            border: 1px solid #dfe1e5;
        }
    </style>
    """, unsafe_allow_html=True)

    if not selection:
        st.info("Geen documenten geselecteerd.")
        return

    tags_html = "".join([f'<span class="tag">{doc}</span>' for doc in selection])
    container_html = f'<div class="tag-container">{tags_html}</div>'
    st.markdown(container_html, unsafe_allow_html=True)