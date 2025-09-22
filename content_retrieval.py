from llm_client import llm_client
from llm_client.document_vector_store import (
    DocumentStore,
    VectorStore,
    SimpleDocument
)
from pipelines.kme_doc import KMEDocument
from config.settings import settings

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
    settings.docstore_folder,
    indexed_metadata_keys=settings.indexed_metadata_keys
)
# summary_doc_store = DocumentStore(
#     "kme_content_summarized",
#     settings.docstore_folder,
#     indexed_metadata_keys=settings.summary_indexed_metadata_keys
# )
vector_store = VectorStore(embedder=embed, 
                        doc_store=doc_store,
                        data_root=settings.docstore_folder)

def query_document(text: str):
    return vector_store.query(text, n_results=10)