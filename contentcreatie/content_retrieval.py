from llm_client import llm_client
from llm_client.document_vector_store import (
    DocumentStore,
    VectorStore,
    SimpleDocument
)
from kme_doc import KMEDocument

        

llm = llm_client.LLMProcessor(client_name='azure',model="gpt-4.1-mini",default_post_process=llm_client.json_post_process)
embed = llm_client.EmbeddingProcessor(client_name="azure",embedding_model='text-embedding-3-large')
doc_store = DocumentStore("kme_content",'data',indexed_metadata_keys=["BELASTINGSOORT","PROCES_ONDERWERP","PRODUCT_SUBONDERWERP",'km_number'])
summary_doc_store = DocumentStore("kme_content_summarized",'data',indexed_metadata_keys=["title","BELASTINGSOORT","PROCES_ONDERWERP","PRODUCT_SUBONDERWERP",'Tags','km_number'])
embedding = VectorStore(embedder=embed,doc_store=summary_doc_store)

def query_document(text:str):
    return embedding.query(text,n_results=10)