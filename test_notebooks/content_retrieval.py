from contentcreatie.llm_client import llm_client
from contentcreatie.llm_client.document_store import (
    DocumentStore,
    SimpleDocument)
from contentcreatie.llm_client.vector_store import  VectorStore
from pipelines.kme_doc import KMEDocument
from contentcreatie.config.settings import settings
from contentcreatie.config.paths import paths

# Get client configurations from settings
llm_client_config = settings.clients.get(settings.llm_client_map.get("gpt-oss-120b"))
embed_client_config = settings.clients.get(settings.embedding_client_map.get(settings.embedding_model))


llm = llm_client.LLMProcessor(
    model="gpt-oss-120b",
    client_config=llm_client_config,
    default_post_process=llm_client.json_decode
)
embed = llm_client.EmbeddingProcessor(
    embedding_model='text-embedding-3-large',
    client_config=embed_client_config
)
doc_store = DocumentStore(
    "kme_content",
    paths.docstore_folder,
    indexed_metadata_keys=settings.indexed_metadata_keys
)

vector_store = VectorStore(embedder=embed, 
                        doc_store=doc_store,
                        data_root=paths.docstore_folder)

def query_document(text: str):
    return vector_store.query(text, n_results=10)