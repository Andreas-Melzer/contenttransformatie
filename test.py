from contentcreatie.storage.storage_service import storage_service
from contentcreatie.storage.mount_manager import mount_manager
from contentcreatie.llm_client.document_store import DocumentStore
from contentcreatie.llm_client.vector_store import VectorStore
from contentcreatie.config.settings import settings
from contentcreatie.config.paths import paths
from contentcreatie.llm_client.llm_client import EmbeddingProcessor, LLMProcessor




storage_service.local_base_path
vertaal_tabel = mount_manager.mount("kme_vertaaltabel.csv")


mount_manager.mounts

import pandas as pd

pd.read_csv(vertaal_tabel,sep=";")

embedding_client_name = settings.embedding_client_map.get(settings.embedding_model)
embedding_config_dict = settings.clients[embedding_client_name].copy()
embedder = EmbeddingProcessor(
    embedding_model=settings.embedding_model,
    client_config=embedding_config_dict
)

doc_store = DocumentStore(
    source_name=settings.raw_doc_store_name,
    data_root=paths.docstore_folder,
    indexed_metadata_keys=settings.indexed_metadata_keys
)
vector_store = VectorStore(embedder=embedder,
                            doc_store=doc_store,
                            data_root=paths.docstore_folder)