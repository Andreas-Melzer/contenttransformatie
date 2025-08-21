# backend/llm_integration.py
from typing import Dict, Any, Tuple, List
import sys 
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from backend.utils.callbacks import tool_callback, tool_result_callback
from llm_client.agent import MultiTurnAgent
from llm_client.llm_client import LLMProcessor, EmbeddingProcessor
from llm_client.document_vector_store import DocumentStore, VectorStore
from llm_client.prompt_builder import PromptBuilder
from llm_client.tools.vector_search_tool import VectorSearchTool
from llm_client.tools.document_shortlist_tool import DocumentShortlistTool
from config.settings import settings # Assuming you have this config available

def load_agent_and_doc_store():
    """
    Loads all necessary components including the LLM, stores, and the agent.
    This replaces the logic from the original `component_loader`.
    """
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

    vs_tool = VectorSearchTool(vector_store=vector_store)
    shortlist_tool = DocumentShortlistTool()
    
    agent = MultiTurnAgent(
        llm_processor=llm,
        prompt_processor=PromptBuilder('prompt_templates', 'search'),
        tools=[vs_tool, shortlist_tool]
    )
    
    return agent, doc_store

def run_agent_chat(agent: MultiTurnAgent, project: Dict[str, Any], query: str) -> Tuple[str, Dict, List]:
    """
    Runs a chat turn with the agent, using callbacks to update project state.
    
    :param agent: The MultiTurnAgent instance.
    :param project: The current project's data dictionary.
    :param query: The user's input query.
    :return: A tuple containing the final response, the updated shortlist, and the updated scratchpad.
    """
    # Define project-specific callbacks to capture state changes
    def on_call_with_project(tool_call):
        tool_callback(tool_call, project)

    def on_result_with_project(tool_result):
        tool_result_callback(tool_result, project)

    # Temporarily attach the project-specific callbacks to the tools.
    # Assumes agent.tools[0] is VectorSearchTool and agent.tools[1] is DocumentShortlistTool
    vs_tool = agent.tools[0]
    shortlist_tool = agent.tools[1]

    original_on_call = shortlist_tool.on_call
    original_on_result = vs_tool.on_result
    
    shortlist_tool.on_call = on_call_with_project
    vs_tool.on_result = on_result_with_project

    # Set up the agent's state from the project
    agent.messages = project.get("messages", [])
    agent.scratchpad = project.get("scratchpad", [])
    
    # Run the chat logic
    final_response = agent.chat(query=query, max_tool_turns=15)
    
    # Detach the callbacks to avoid side effects in other sessions
    shortlist_tool.on_call = original_on_call
    vs_tool.on_result = original_on_result

    # The 'project' dictionary is modified in-place by the callbacks.
    return final_response, project["shortlist"], agent.scratchpad