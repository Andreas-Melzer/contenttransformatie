import streamlit as st
from config.settings import settings
from llm_client.llm_client import LLMProcessor, EmbeddingProcessor
from llm_client.document_vector_store import DocumentStore, VectorStore
from llm_client.agent import MultiTurnAgent
from llm_client.prompt_builder import PromptBuilder
from llm_client.tools.vector_search_tool import VectorSearchTool
from llm_client.tools.document_shortlist_tool import DocumentShortlistTool
from interface.utils.callbacks import streamlit_tool_callback, streamlit_tool_result_callback
from typing import Dict

@st.cache_resource
def load_heavy_components():
    """Laadt de componenten die niet afhankelijk zijn van de project-staat."""
    print("Initializing heavy components (LLM, Embedder, Stores)...")
    llm = LLMProcessor(model=settings.llm_model)
    embedder = EmbeddingProcessor(embedding_model=settings.embedding_model)
    doc_store = DocumentStore(
        settings.raw_doc_store_name,
        settings.data_root,
        settings.indexed_metadata_keys
    )
    summary_doc_store = DocumentStore(
        settings.summary_doc_store_name,
        settings.data_root,
        settings.summary_indexed_metadata_keys
    )
    vector_store = VectorStore(embedder=embedder, doc_store=summary_doc_store)
    return llm, embedder, doc_store, vector_store

def load_components(project: Dict):
    """Laadt alle componenten en configureert de agent voor een specifiek project."""
    llm, embedder, doc_store, vector_store = load_heavy_components()

    # Gebruik een lambda om de project-context mee te geven aan de callbacks
    on_call_with_project = lambda tool_call: streamlit_tool_callback(tool_call, project)
    on_result_with_project = lambda tool_result: streamlit_tool_result_callback(tool_result, project)

    # Initialiseer de tools met de project-specifieke callbacks
    vs_tool = VectorSearchTool(
        vector_store=vector_store,
        on_result=on_result_with_project
    )
    shortlist_tool = DocumentShortlistTool(
        on_call=on_call_with_project
    )

    # Initialiseer de agent
    agent = MultiTurnAgent(
        llm_processor=llm,
        prompt_processor=PromptBuilder('prompt_templates', 'search'),
        tools=[vs_tool, shortlist_tool]
    )

    return agent, doc_store