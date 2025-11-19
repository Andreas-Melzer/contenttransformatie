import streamlit as st
from typing import Literal, Dict, Tuple, List

from contentcreatie.config.settings import settings
from contentcreatie.config.paths import paths
from project import Project
from utils.callbacks import (list_documents_callback,
                               streamlit_tool_callback,
                               search_results_callback)
from contentcreatie.llm_client.agent import MultiTurnAgent
from contentcreatie.llm_client.document_store import DocumentStore
from contentcreatie.llm_client.vector_store import VectorStore
from contentcreatie.llm_client.llm_client import EmbeddingProcessor, LLMProcessor
from contentcreatie.llm_client.prompt_builder import PromptBuilder
from implementations.tools.document_relevance_tool import DocumentRelevanceTool,ToolBase
from implementations.tools.list_selected_documents_tool import ListSelectedDocumentsTool
from implementations.tools.read_documents_tool import ReadDocumentsTool
from implementations.tools.vector_search_tool import VectorSearchTool
from implementations.tools.save_consolidated_json_tool import SaveConsolidatedJsonTool
from implementations.tools.save_rewritten_json_tool import SaveRewrittenJsonTool

AgentType = Literal["search", "consolidate", "rewrite"]

@st.cache_resource
def load_heavy_components() -> Tuple[LLMProcessor, DocumentStore, VectorStore]:
    """
    Loads and caches heavy components (LLM, Embedder, Stores) using
    Streamlit's global resource cache. This runs only ONCE per app start.

    :return: Tuple[LLMProcessor, DocumentStore, VectorStore], The initialized components.
    :raises ValueError: If client configurations are missing or invalid in settings.
    """
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
        paths.docstore_folder,
        settings.indexed_metadata_keys
    )
    vector_store = VectorStore(embedder=embedder,
                               doc_store=doc_store,
                               data_root=paths.docstore_folder)
    
    return llm, doc_store, vector_store

def _initialize_search_tools(project: Project, vector_store: VectorStore, doc_store: DocumentStore) -> List[ToolBase]:
    on_call_with_project = lambda tool_call: streamlit_tool_callback(tool_call, project)
    on_list_documents = lambda tool_result: list_documents_callback(tool_result, project)

    vector_search_tool = VectorSearchTool(
        vector_store=vector_store,
        on_result=lambda tool_result: search_results_callback(tool_result, project),
        metadata_filter=project.get_domain_filter()
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
    return [vector_search_tool, document_relevance_tool, list_tool, read_tool]

def _initialize_consolidate_tools(project: Project, vector_store: VectorStore, doc_store: DocumentStore) -> List[ToolBase]:
    on_call_with_project = lambda tool_call: streamlit_tool_callback(tool_call, project)
    
    save_consolidated_json_tool = SaveConsolidatedJsonTool(
        project=project,
        on_call=on_call_with_project
    )
    return [save_consolidated_json_tool]

def _initialize_rewrite_tools(project: Project, vector_store: VectorStore, doc_store: DocumentStore) -> List[ToolBase]:
    on_call_with_project = lambda tool_call: streamlit_tool_callback(tool_call, project)
    
    save_rewritten_json_tool = SaveRewrittenJsonTool(
        project=project,
        on_call=on_call_with_project
    )
    return [save_rewritten_json_tool]

# --- Agent Initializers ---

def _initialize_search_agent_for_project(project: Project, llm: LLMProcessor, vector_store: VectorStore, doc_store: DocumentStore) -> MultiTurnAgent:
    """Initialiseert en configureert de search agent voor een specifiek project."""
    return MultiTurnAgent(
        llm_processor=llm,
        prompt_processor=PromptBuilder('contentcreatie/prompt_templates', 'search'),
        tools=_initialize_search_tools(project, vector_store, doc_store),
        messages=project.search_messages
    )
    
def _initialize_consolidate_agent_for_project(project: Project, llm: LLMProcessor, vector_store: VectorStore, doc_store: DocumentStore) -> MultiTurnAgent:
    """Initialiseert en configureert de consolidate agent voor een specifiek project."""
    return MultiTurnAgent(
        llm_processor=llm,
        prompt_processor=PromptBuilder('contentcreatie/prompt_templates', 'consolidate'),
        tools=_initialize_consolidate_tools(project, vector_store, doc_store),
        messages=project.consolidate_messages
    )
    
def _initialize_rewrite_agent_for_project(project: Project, llm: LLMProcessor, vector_store: VectorStore, doc_store: DocumentStore) -> MultiTurnAgent:
    """Initialiseert en configureert de rewrite agent voor een specifiek project."""
    return MultiTurnAgent(
        llm_processor=llm,
        prompt_processor=PromptBuilder('contentcreatie/prompt_templates', 'rewrite'),
        tools=_initialize_rewrite_tools(project, vector_store, doc_store),
        messages=project.rewrite_messages
    )

AGENT_INITIALIZERS = {
    "search": _initialize_search_agent_for_project,
    "consolidate": _initialize_consolidate_agent_for_project,
    "rewrite": _initialize_rewrite_agent_for_project,
}

def get_agent(project: Project, agent_type: AgentType) -> MultiTurnAgent:
    """
    A factory function to get or create an agent for a specific project.
    
    It uses `st.session_state` to cache agents per project, per session.
    It uses `st.cache_resource` (via `load_heavy_components`) to get
    the globally shared LLM and data stores.
    
    :param project: Project, The project object, containing state (like messages).
    :param agent_type: AgentType, The type of agent to retrieve ("search", "consolidate", "rewrite").
    :return: MultiTurnAgent, The cached or newly created agent instance.
    :raises RuntimeError: If heavy components fail to load.
    """
    
    if "agents" not in st.session_state:
        st.session_state.agents: Dict[str, MultiTurnAgent] = {}

    agent_key = f"{project.id}_{agent_type}"

    cached_agent = st.session_state.agents.get(agent_key)
    if cached_agent:
        return cached_agent
    
    llm, doc_store, vector_store = load_heavy_components()
    
    if not llm or not doc_store or not vector_store:
         raise RuntimeError("Heavy components not loaded correctly.")
            
    initializer_func = AGENT_INITIALIZERS.get(agent_type)
    if not initializer_func:
        raise ValueError(f"No initializer found for agent type: {agent_type}")
    
    new_agent = initializer_func(project, llm, vector_store, doc_store)
    
    st.session_state.agents[agent_key] = new_agent
    return new_agent