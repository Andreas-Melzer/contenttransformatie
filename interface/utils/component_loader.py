import json

import streamlit as st
from interface.project import Project

from config.settings import settings
from interface.utils.callbacks import (list_documents_callback,
                                       streamlit_tool_callback,
                                       streamlit_tool_result_callback)
from llm_client.agent import MultiTurnAgent
from llm_client.document_vector_store import DocumentStore, VectorStore
from llm_client.llm_client import EmbeddingProcessor, LLMProcessor
from llm_client.prompt_builder import PromptBuilder
from implementations.tools.document_shortlist_tool import DocumentShortlistTool
from implementations.tools.list_selected_documents_tool import \
    ListSelectedDocumentsTool
from implementations.tools.read_documents_tool import ReadDocumentsTool
from implementations.tools.vector_search_tool import VectorSearchTool


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
    return llm, doc_store,summary_doc_store, vector_store



def initialize_agent_for_project(project: Project, llm: LLMProcessor, vector_store: VectorStore, summary_doc_store : DocumentStore) -> MultiTurnAgent:
    """Initialiseert en configureert de agent voor een specifiek project."""
    
    # Gebruik een lambda om de project-context mee te geven aan de callbacks
    on_call_with_project = lambda tool_call: streamlit_tool_callback(tool_call, project)
    on_result_with_project = lambda tool_result: streamlit_tool_result_callback(tool_result, project)
    on_list_documents = lambda tool_result: list_documents_callback(tool_result, project)
    # Initialiseer de tools met de project-specifieke callbacks
    vs_tool = VectorSearchTool(
        vector_store=vector_store,
        on_result=on_result_with_project
    )
    shortlist_tool = DocumentShortlistTool(
        on_call=on_call_with_project
    )
    list_tool = ListSelectedDocumentsTool(
        on_result=on_list_documents
    )
    read_tool = ReadDocumentsTool(
        doc_store=summary_doc_store
    )

    # Initialiseer de agent
    agent = MultiTurnAgent(
        llm_processor=llm,
        prompt_processor=PromptBuilder('prompt_templates', 'search'),
        tools=[vs_tool, shortlist_tool, list_tool, read_tool]
    )
    return agent