import sys
import os
sys.path.append(os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'contentcreatie'))

from nicegui import ui
from config.settings import settings
from llm_client.llm_client import LLMProcessor, EmbeddingProcessor
from llm_client.document_vector_store import DocumentStore, VectorStore
from llm_client.agent import MultiTurnAgent
from llm_client.prompt_builder import PromptBuilder
from llm_client.tools.vector_search_tool import VectorSearchTool
from llm_client.tools.document_shortlist_tool import DocumentShortlistTool
from nicegui_interface.utils.callbacks import nicegui_tool_callback, nicegui_tool_result_callback
from typing import Dict, Tuple

# Cache for heavy components
_heavy_components = None

def load_heavy_components():
    """Laadt de componenten die niet afhankelijk zijn van de project-staat."""
    global _heavy_components
    if _heavy_components is None:
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
        _heavy_components = (llm, embedder, doc_store, vector_store)
    return _heavy_components

def load_components(project: Dict) -> Tuple[MultiTurnAgent, DocumentStore]:
    """Laadt alle componenten en configureert de agent voor een specifiek project."""
    llm, embedder, doc_store, vector_store = load_heavy_components()
    
    # Gebruik een lambda om de project-context mee te geven aan de callbacks
    on_call_with_project = lambda tool_call: nicegui_tool_callback(tool_call, project)
    on_result_with_project = lambda tool_result: nicegui_tool_result_callback(tool_result, project)
    
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