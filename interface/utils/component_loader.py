
import streamlit as st

from config.settings import settings
from interface.project import Project
from interface.utils.callbacks import (list_documents_callback,
                                       streamlit_tool_callback,
                                       search_results_callback)
from llm_client.agent import MultiTurnAgent
from llm_client.document_vector_store import DocumentStore, VectorStore
from llm_client.llm_client import EmbeddingProcessor, LLMProcessor
from llm_client.prompt_builder import PromptBuilder
from interface.implementations.tools.document_relevance_tool import DocumentRelevanceTool
from interface.implementations.tools.list_selected_documents_tool import \
    ListSelectedDocumentsTool
from interface.implementations.tools.read_documents_tool import ReadDocumentsTool
from interface.implementations.tools.vector_search_tool import VectorSearchTool
from interface.implementations.tools.save_consolidated_json_tool import SaveConsolidatedJsonTool
from interface.implementations.tools.save_rewritten_json_tool import SaveRewrittenJsonTool


@st.cache_resource
def load_heavy_components():
    """Laadt de componenten die niet afhankelijk zijn van de project-staat."""
    print("Initializing heavy components (LLM, Embedder, Stores)...")

    llm_client_name = settings.llm_client_map.get(settings.llm_model)
    if not llm_client_name or llm_client_name not in settings.clients:
        raise ValueError(f"Client '{llm_client_name}' for model '{settings.llm_model}' not found or configured in settings.")

    llm_config_dict = settings.clients[llm_client_name].copy()
    llm_config_dict['type'] = 'azure' if 'azure' in llm_client_name else llm_client_name

    llm = LLMProcessor(
        model=settings.llm_model,
        client_config=llm_config_dict
    )

    embedding_client_name = settings.embedding_client_map.get(settings.embedding_model)
    if not embedding_client_name or embedding_client_name not in settings.clients:
        raise ValueError(f"Client '{embedding_client_name}' for model '{settings.embedding_model}' not found or configured in settings.")
        
    embedding_config_dict = settings.clients[embedding_client_name].copy()
    embedding_config_dict['type'] = 'azure' if 'azure' in embedding_client_name else embedding_client_name

    embedder = EmbeddingProcessor(
        embedding_model=settings.embedding_model,
        client_config=embedding_config_dict
    )
    doc_store = DocumentStore(
        settings.raw_doc_store_name,
        settings.docstore_folder,
        settings.indexed_metadata_keys
    )
    vector_store = VectorStore(embedder=embedder,
                               doc_store=doc_store,
                               data_root=settings.docstore_folder)

    return llm, doc_store, vector_store


def initialize_search_tools(project: Project,vector_store: VectorStore, doc_store : DocumentStore):
    on_call_with_project = lambda tool_call: streamlit_tool_callback(tool_call, project)
    on_list_documents = lambda tool_result: list_documents_callback(tool_result, project)

    vector_search_tool = VectorSearchTool(
        vector_store=vector_store,
        on_result=lambda tool_result: search_results_callback(tool_result, project)
    )
    document_relevance_tool = DocumentRelevanceTool(
        on_call=on_call_with_project
    )
    list_tool = ListSelectedDocumentsTool(
        on_result=on_list_documents
    )
    read_tool = ReadDocumentsTool(
        doc_store=doc_store
    )
    return [vector_search_tool,document_relevance_tool,list_tool,read_tool]

def initialize_consolidate_tools(project: Project,vector_store: VectorStore, doc_store : DocumentStore):
    on_call_with_project = lambda tool_call: streamlit_tool_callback(tool_call, project)
    
    save_consolidated_json_tool = SaveConsolidatedJsonTool(
        project=project,
        on_call=on_call_with_project
    )
    return [save_consolidated_json_tool]

def initialize_rewrite_tools(project: Project,vector_store: VectorStore, doc_store : DocumentStore):
    on_call_with_project = lambda tool_call: streamlit_tool_callback(tool_call, project)
    
    save_rewritten_json_tool = SaveRewrittenJsonTool(
        project=project,
        on_call=on_call_with_project
    )
    return [save_rewritten_json_tool]


def initialize_agent_for_project(project: Project, llm: LLMProcessor, vector_store: VectorStore, doc_store : DocumentStore) -> MultiTurnAgent:
    """Initialiseert en configureert de agent voor een specifiek project."""
    agent = MultiTurnAgent(
        llm_processor=llm,
        prompt_processor=PromptBuilder('prompt_templates', 'search'),
        tools=initialize_search_tools(project,vector_store,doc_store),
        messages=project.messages
    )
    return agent
    
def initialize_consolidate_agent_for_project(project: Project, llm: LLMProcessor, vector_store: VectorStore, doc_store : DocumentStore) -> MultiTurnAgent:
    """Initialiseert en configureert de consolidate agent voor een specifiek project."""
    
    agent = MultiTurnAgent(
        llm_processor=llm,
        prompt_processor=PromptBuilder('prompt_templates', 'consolidate'),
        tools=initialize_consolidate_tools(project,vector_store,doc_store),
        messages=project.consolidate_messages
    )
    return agent
    
def initialize_rewrite_agent_for_project(project: Project, llm: LLMProcessor, vector_store: VectorStore, doc_store : DocumentStore) -> MultiTurnAgent:
    """Initialiseert en configureert de rewrite agent voor een specifiek project."""
    
    agent = MultiTurnAgent(
        llm_processor=llm,
        prompt_processor=PromptBuilder('prompt_templates', 'rewrite'),
        tools=initialize_rewrite_tools(project,vector_store,doc_store),
        messages=project.rewrite_messages
    )
    return agent