import typer
from rich.console import Console

from config.settings import settings
from llm_client.llm_client import LLMProcessor, EmbeddingProcessor
from llm_client.document_vector_store import DocumentStore, VectorStore
from llm_client.agent import MultiTurnAgent
from llm_client.prompt_builder import PromptBuilder
from llm_client.tools.vector_search_tool import VectorSearchTool
from llm_client.tools.document_shortlist_tool import DocumentShortlistTool
from pipelines.data_ingestion import DataIngestionPipeline

app = typer.Typer()
console = Console()

@app.command()
def ingest_data():
    """Runs the data ingestion pipeline to process new documents."""
    llm = LLMProcessor(model=settings.llm_model, default_post_process=lambda x: x)
    doc_store = DocumentStore(settings.raw_doc_store_name, settings.data_root, settings.indexed_metadata_keys)
    summary_doc_store = DocumentStore(settings.summary_doc_store_name, settings.data_root, settings.summary_indexed_metadata_keys)

    pipeline = DataIngestionPipeline(settings, llm, doc_store, summary_doc_store)
    pipeline.run()

@app.command()
def chat():
    """Starts an interactive chat session with the RAG agent."""
    llm = LLMProcessor( model=settings.llm_model)
    embed = EmbeddingProcessor(embedding_model=settings.embedding_model)
    summary_doc_store = DocumentStore(settings.summary_doc_store_name, settings.data_root, settings.summary_indexed_metadata_keys)
    embedding = VectorStore(embedder=embed, doc_store=summary_doc_store)

    vs_tool = VectorSearchTool(vector_store=embedding)
    slt = DocumentShortlistTool()
    prompt_processor = PromptBuilder('prompt_templates', 'search')
    agent = MultiTurnAgent(
        llm_processor=llm,
        prompt_processor=prompt_processor,
        tools=[vs_tool, slt]
    )

    console.print("[bold green]Starting chat session with the agent. Type 'exit' to end.[/bold green]")
    while True:
        query = console.input("[bold blue]You: [/bold blue]")
        if query.lower() == "exit":
            break
        response = agent.chat(query=query, max_tool_turns=15)
        console.print(f"[bold yellow]Agent:[/bold yellow] {response}")


if __name__ == "__main__":
    app()
