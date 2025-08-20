import os
import json
from typing import List, Optional
from .llm_client import EmbeddingProcessor
from dataclasses import dataclass
from typing import Dict, Any
import pickle
from abc import ABC
from typing import Dict, Any, List, Optional
import numpy as np
import faiss
import os
import hashlib 
import pickle
from typing import List, Dict, Optional, Union
from whoosh.index import create_in, open_dir, exists_in
from whoosh.fields import Schema, ID, TEXT
from whoosh.qparser import MultifieldParser, QueryParser
import shutil

@dataclass
class Document(ABC):
    """An abstract base class for a document.

    :param id: str, The unique identifier for the document.
    :param title: str, The title of the document.
    :param content: str, The main text content of the document.
    :param metadata: Dict[str, Any], A dictionary for any additional metadata.
    """
    id: str
    title: str
    content: str
    metadata: Dict[str, Any]

    @property
    def content_to_embed(self) -> str:
        """The string content that will be used for generating embeddings.
        
        This can be overridden by subclasses to create more sophisticated embeddings,
        for example, by combining the title and content.

        :return: str, The text to be embedded.
        """
        return self.content
    
@dataclass
class SimpleDocument(Document):
    """A basic, concrete implementation of the Document class."""
    pass

class DocumentStore:
    """Manages document storage, persistence, and indexed metadata searching."""
    def __init__(
        self,
        source_name: str,
        data_root: str = "data",
        indexed_metadata_keys: Optional[List[str]] = None
    ):
        """Initializes the DocumentStore, handling persistence and metadata indexing.
        :param source_name: str, A unique name for the data source, used for creating storage directories.
        :param data_root: str, The root directory where data will be stored, defaults to "data"
        :param indexed_metadata_keys: Optional[List[str]], A list of metadata keys to be indexed for fast text-based searching, defaults to None
        """
        self.source_name = source_name
        self.data_root = data_root
        self.indexed_metadata_keys = indexed_metadata_keys or []
        
        store_path = os.path.join(self.data_root, self.source_name)
        os.makedirs(store_path, exist_ok=True)
        self.persistence_file = os.path.join(store_path, "documents.pkl")
        self.documents: Dict[str, Document] = self._load()
        
        index_path = os.path.join(store_path, "metadata_index")
        
        schema_fields = {'doc_id': ID(stored=True, unique=True)}
        for key in self.indexed_metadata_keys:
            schema_fields[key] = TEXT(stored=True, phrase=False)
        self.schema = Schema(**schema_fields)


        if exists_in(index_path):
            self.ix = open_dir(index_path, schema=self.schema)
        else:
            os.makedirs(index_path, exist_ok=True)
            self.ix = create_in(index_path, self.schema)
            
        if self.indexed_metadata_keys:
            self.query_parser = MultifieldParser(self.indexed_metadata_keys, schema=self.schema)
        else:
            self.query_parser = None

    def rebuild_search_index(self):
        """Rebuilds the Whoosh search index from scratch for all documents in the store.
        
        This method should be called if the indexed metadata keys change or if the index
        is suspected to be corrupt. It will delete the old index and create a new one.
        """
        if not self.indexed_metadata_keys:
            print("Warning: No metadata keys configured for indexing. Cannot build index.")
            return
        print(f"Rebuilding search index for {len(self.documents)} documents...")
        index_path = os.path.join(self.data_root, self.source_name, "metadata_index")
        if os.path.exists(index_path):
            shutil.rmtree(index_path)
        os.makedirs(index_path)
        self.ix = create_in(index_path, self.schema)
        all_docs = self.get_all()
        if not all_docs:
            print("No documents in store. Index is empty.")
            return
        writer = self.ix.writer()
        for doc in all_docs:
            doc_for_index = {'doc_id': doc.id}
            for key in self.indexed_metadata_keys:
                value = doc.metadata.get(key)
                doc_for_index[key] = str(value) if value is not None else None
            writer.add_document(**doc_for_index)
        writer.commit()
        print(f"Successfully indexed {len(all_docs)} documents.")

    def add(self, docs_to_add: Union[Document, List[Document]], refresh: bool = False):
        """Adds or updates one or more documents in the store and search index.
        
        If a document with the same ID already exists, it is updated. The change is
        persisted to disk.
        
        :param docs_to_add: Union[Document, List[Document]], The document or list of documents to add.
        :param refresh: bool, If True, forces an update even if the document appears unchanged, defaults to False
        """
        if not isinstance(docs_to_add, list): docs_to_add = [docs_to_add]
        writer = self.ix.writer() if self.indexed_metadata_keys else None
        changed = False
        for doc in docs_to_add:
            if refresh or doc.id not in self.documents or self.documents[doc.id] != doc:
                self.documents[doc.id] = doc
                changed = True
                if writer:
                    doc_for_index = {'doc_id': doc.id}
                    for key in self.indexed_metadata_keys:
                        value = doc.metadata.get(key)
                        doc_for_index[key] = str(value) if value is not None else None
                    writer.update_document(**doc_for_index)
        if changed:
            if writer: writer.commit()
            self._save()
    
    def search(self, query_string: str, limit: int = 10) -> List[Document]:
        """Searches the indexed metadata fields using a Whoosh query string.
        :param query_string: str, The query string to search for (e.g., 'status:open AND type:bug').
        :param limit: int, The maximum number of documents to return, defaults to 10
        :return: List[Document], A list of matching documents.
        """
        if not self.query_parser:
            print("Warning: No metadata keys were indexed. Cannot perform search.")
            return []
        results = []
        with self.ix.searcher() as searcher:
            query = self.query_parser.parse(query_string)
            hits = searcher.search(query, limit=limit)
            for hit in hits:
                if doc := self.get(hit['doc_id']):
                    results.append(doc)
        return results
        
    def _load(self) -> Dict[str, Document]:
        """Loads the document dictionary from a pickle file.
        :return: Dict[str, Document], The dictionary of documents loaded from disk.
        """
        if not os.path.exists(self.persistence_file): return {}
        try:
            with open(self.persistence_file, 'rb') as f: return pickle.load(f)
        except (IOError, pickle.PickleError): return {}
        
    def _save(self):
        """Saves the current document dictionary to a pickle file."""
        with open(self.persistence_file, 'wb') as f: pickle.dump(self.documents, f)
        
    def get(self, doc_id: str) -> Optional[Document]:
        """Retrieves a single document by its ID.
        :param doc_id: str, The ID of the document to retrieve.
        :return: Optional[Document], The document if found, otherwise None.
        """
        return self.documents.get(doc_id)
        
    def get_all(self) -> List['Document']:
        """Retrieves all documents from the store.
        :return: List[Document], A list of all documents.
        """
        return list(self.documents.values())
        
    def get_all_ids(self) -> List[str]:
        """Retrieves the IDs of all documents in the store.
        :return: List[str], A list of all document IDs.
        """
        return list(self.documents.keys())

def get_stable_id(doc_id: str) -> int:
    """Generates a stable 64-bit integer ID from a string."""
    return int(hashlib.sha256(doc_id.encode('utf-8')).hexdigest(), 16) & (2**63 - 1)

class VectorStore:
    """Manages vector embeddings and performs similarity searches using FAISS."""
    def __init__(self, embedder: 'EmbeddingProcessor', doc_store: DocumentStore, data_root: str = "data"):
        """Initializes the VectorStore.
        
        Manages vector embeddings and performs similarity searches using FAISS. It links
        to a DocumentStore and an EmbeddingProcessor.
        
        :param embedder: EmbeddingProcessor, The processor used to generate text embeddings.
        :param doc_store: DocumentStore, The store where the source documents are kept.
        :param data_root: str, The root directory for storing the FAISS index and other data, defaults to "data"
        """
        self.embedder = embedder
        self.doc_store = doc_store
        
        model_name = self.embedder.embedding_model.replace("/", "_")
        store_path = os.path.join(data_root, self.doc_store.source_name, model_name)
        os.makedirs(store_path, exist_ok=True)
        
        self.index_file = os.path.join(store_path, "vectors.faiss")
        self.ids_file = os.path.join(store_path, "indexed_ids.pkl")
        
        self.indexed_ids: set[int] = set()
        
        self._load_or_initialize()
        self.sync_with_store()

    def _load_or_initialize(self):
        """Loads an existing FAISS index from disk or initializes a new one if not found."""
        if os.path.exists(self.index_file) and os.path.exists(self.ids_file):
            self.index = faiss.read_index(self.index_file)
            with open(self.ids_file, 'rb') as f:
                self.indexed_ids = pickle.load(f)
            print(f"Loaded FAISS index ({self.index.ntotal} vectors) and ID set from disk.")
        else:
            dummy_embedding = self.embedder.embed("test")
            dim = len(dummy_embedding)
            self.index = faiss.IndexIDMap(faiss.IndexFlatL2(dim))
            self.indexed_ids = set()
            print(f"Initialized new FAISS index with dimension {dim}.")

    def _save(self):
        """Saves the current FAISS index and the set of indexed IDs to disk."""
        faiss.write_index(self.index, self.index_file)
        with open(self.ids_file, 'wb') as f:
            pickle.dump(self.indexed_ids, f)
        print(f"Saved FAISS index ({self.index.ntotal} vectors) and ID set.")

    def add(self, docs: Union[Document, List[Document]], refresh: bool = False):
        """Adds or updates documents and their vector embeddings.
        
        This method first adds the document(s) to the underlying DocumentStore, then
        creates embeddings for them and adds the vectors to the FAISS index.
        
        :param docs: Union[Document, List[Document]], The document or list of documents to add/update.
        :param refresh: bool, If True, forces an update in the DocumentStore, defaults to False
        """
        if not isinstance(docs, list):
            docs = [docs]
            
        self.doc_store.add(docs, refresh=refresh)

        hashed_ids = np.array([get_stable_id(doc.id) for doc in docs])
        
        if self.index.ntotal > 0:
            self.index.remove_ids(hashed_ids)
            self.indexed_ids.difference_update(hashed_ids)
        
        content_to_embed = [doc.content_to_embed for doc in docs]
        if not content_to_embed:
            if self.index.ntotal > 0: self._save()
            return

        embeddings = self.embedder.embed(content_to_embed)
        embeddings_np = np.array(embeddings).astype('float32')
        
        self.index.add_with_ids(embeddings_np, hashed_ids)
        self.indexed_ids.update(hashed_ids)
        self._save()

    def sync_with_store(self, refresh: bool = False):
        """Ensures the vector index is in sync with the document store.
        
        In normal mode, it checks for and indexes any documents present in the
        DocumentStore but not in the vector index. In refresh mode, it rebuilds
        the entire vector index from scratch based on the DocumentStore.
        
        :param refresh: bool, If True, rebuilds the entire index. If False, only adds missing documents, defaults to False
        """
        print("Syncing VectorStore with DocumentStore...")
        if refresh:
            print("Refresh mode enabled: Re-building the entire index from the DocumentStore.")
            all_docs = self.doc_store.get_all()
            
            dummy_embedding = self.embedder.embed("test")
            dim = len(dummy_embedding)
            self.index = faiss.IndexIDMap(faiss.IndexFlatL2(dim))
            self.indexed_ids = set()
            
            if not all_docs:
                print("DocumentStore is empty. Index has been cleared.")
                self._save()
                print("Sync complete.")
                return
            
            print(f"Re-indexing {len(all_docs)} documents...")
            content_to_embed = [doc.content_to_embed for doc in all_docs]
            embeddings = self.embedder.embed(content_to_embed)
            embeddings_np = np.array(embeddings).astype('float32')
            
            hashed_ids = np.array([get_stable_id(doc.id) for doc in all_docs])
            
            self.index.add_with_ids(embeddings_np, hashed_ids)
            self.indexed_ids.update(hashed_ids)
        else:
            all_doc_ids = self.doc_store.get_all_ids()
            docs_to_index = []
            for doc_id in all_doc_ids:
                hashed_id = get_stable_id(doc_id)
                if hashed_id not in self.indexed_ids:
                    doc = self.doc_store.get(doc_id)
                    if doc:
                        docs_to_index.append(doc)
            
            if not docs_to_index:
                print("VectorStore is already in sync. No new documents to add.")
                return
            
            print(f"Found {len(docs_to_index)} documents missing from index. Adding them now...")
            self.add(docs_to_index, refresh=False)
        self._save()
        print("Sync complete.")

    def query(self, query_text: str, n_results: int = 5) -> List[Dict]:
        """Performs a semantic similarity search for a given query text.
        
        Embeds the query text and uses FAISS to find the most similar documents
        based on vector distance.
        
        :param query_text: str, The text to search for.
        :param n_results: int, The number of top matching documents to return, defaults to 5
        :return: List[Dict], A list of dictionaries, each containing a 'document' and its 'distance' score.
        """
        query_embedding = self.embedder.embed(query_text)
        query_np = np.array([query_embedding]).astype('float32')
        
        if self.index.ntotal == 0:
            return []
            
        distances, hashed_ids = self.index.search(query_np, min(n_results, self.index.ntotal))
        
        all_doc_ids = self.doc_store.get_all_ids()
        # --- HASHING FIX ---
        hashed_id_map = {get_stable_id(doc_id): doc_id for doc_id in all_doc_ids}

        results = []
        for i, hashed_id in enumerate(hashed_ids[0]):
            doc_id = hashed_id_map.get(int(hashed_id)) # Cast to int for safety
            if doc_id:
                doc = self.doc_store.get(doc_id)
                if doc:
                    results.append({
                        'document': doc,
                        'distance': float(distances[0][i])
                    })
        return results