import hashlib
import json
import os
import pickle
import shutil
from abc import ABC
from dataclasses import dataclass, asdict
from typing import Any, Dict, List, Optional, Union, Set
from whoosh.index import LockError
import faiss
import numpy as np
import pandas as pd  # Added import
from whoosh.fields import ID, TEXT, Schema
from whoosh.index import create_in, exists_in, open_dir
from whoosh.qparser import MultifieldParser, QueryParser
from config.logger import get_logger
from .llm_client import EmbeddingProcessor

logger = get_logger()

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
        
        self.store_path = os.path.join(self.data_root, self.source_name)
        os.makedirs(self.store_path, exist_ok=True)
        
        self.persistence_file = os.path.join(self.store_path, "documents.parquet")
        self.documents: Dict[str, Document] = self._load()
        
        self.index_path = os.path.join(self.store_path, "metadata_index")
        
        schema_fields = {'doc_id': ID(stored=True, unique=True)}
        for key in self.indexed_metadata_keys:
            schema_fields[key] = TEXT(stored=True, phrase=False)
        self.schema = Schema(**schema_fields)


        if exists_in(self.index_path):
            self.ix = open_dir(self.index_path, schema=self.schema)
        else:
            os.makedirs(self.index_path, exist_ok=True)
            self.ix = create_in(self.index_path, self.schema)
            
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

    def add(self, 
            docs_to_add: Union[Document, List[Document]], 
            refresh: bool = False, 
            update_index: bool = False,
            save = False
           ):
        """Adds or updates one or more documents in the store and search index.
        
        If a document with the same ID already exists, it is updated. The change is
        persisted to disk.
        
        :param docs_to_add: Union[Document, List[Document]], The document or list of documents to add.
        :param refresh: bool, If True, forces an update even if the document appears unchanged, defaults to False
        :param update_index: bool, If True, updates the Whoosh index. If False, only saves to the JSON store, defaults to True
        """
        if not isinstance(docs_to_add, list): 
            docs_to_add = [docs_to_add]
        
        writer = None
        if self.ix and self.indexed_metadata_keys and update_index:
            writer = self.ix.writer()
            writer = None 

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
            if writer: 
                writer.commit()
            if save:
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

    def clear(self):
        """Clears all documents from the store and the search index.
        
        This deletes the persistence file and rebuilds the Whoosh index from scratch.
        """
        print(f"Clearing DocumentStore at {self.store_path}...")
        self.documents = {}
        
        if os.path.exists(self.persistence_file):
            os.remove(self.persistence_file)
            
        if os.path.exists(self.index_path):
            shutil.rmtree(self.index_path)
        os.makedirs(self.index_path, exist_ok=True)
        self.ix = create_in(self.index_path, self.schema)
        
        print("DocumentStore cleared.")

    def get_doc_ids_by_metadata(self, metadata_filter: Dict[str, Any]) -> Set[str]:
        """Gets a set of document IDs that match a metadata filter.
        
        This performs an exact match on all key-value pairs in the filter.
        
        :param metadata_filter: Dict[str, Any], The key-value pairs to filter by.
        :return: Set[str], A set of matching document IDs.
        """
        if not metadata_filter:
            return set(self.get_all_ids())
            
        matching_ids = set()
        for doc_id, doc in self.documents.items():
            match = True
            for key, value in metadata_filter.items():
                if doc.metadata.get(key) != value:
                    match = False
                    break
            if match:
                matching_ids.add(doc_id)
        return matching_ids
    
    def contains(self,id:str):
        return id in self.documents
        
    def _load(self) -> Dict[str, Document]:
        """Loads the document dictionary from a Parquet file.
        :return: Dict[str, Document], The dictionary of documents loaded from disk.
        """
        logger.info("Loading document store from disk")
        if not os.path.exists(self.persistence_file):
            return {}
        try:
            df = pd.read_parquet(self.persistence_file)
            if df.empty:
                return {}

            df['metadata'] = df['metadata'].apply(json.loads)
            
            documents = {}
            for record in df.to_dict('records'):
                doc = SimpleDocument(**record) 
                documents[doc.id] = doc
            return documents
        except Exception as e:
            print(f"Error loading Parquet file {self.persistence_file}: {e}. Returning empty store.")
            return {}
        
    # --- MODIFIED: Replaced Pickle logic with Parquet logic ---
    def _save(self):
        """Saves the current document dictionary to a Parquet file."""
        if not self.documents:
            # Save an empty DataFrame with the correct schema
            df = pd.DataFrame(columns=['id', 'title', 'content', 'metadata'])
        else:
            # Convert dict of Document objects to a list of dicts
            doc_list = [asdict(doc) for doc in self.documents.values()]
            df = pd.DataFrame.from_records(doc_list)
            
            # Serialize the metadata dict to a JSON string for Parquet compatibility
            df['metadata'] = df['metadata'].apply(json.dumps)
        
        try:
            # Save to Parquet using pyarrow engine
            df.to_parquet(self.persistence_file, index=False, engine='pyarrow')
        except Exception as e:
            print(f"Error saving Parquet file {self.persistence_file}: {e}")
    
    # --- MODIFIED: Fixed bug (was _save() instead of self._save()) ---
    def save(self):
        """Public method to trigger a save of the document store."""
        self._save()
        
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

# --- No changes below this line ---

def get_stable_id(doc_id: str) -> int:
    """Generates a stable 64-bit integer ID from a string."""
    return int(hashlib.sha256(doc_id.encode('utf-8')).hexdigest(), 16) & (2**63 - 1)


def _batched(seq, size: int):
    for i in range(0, len(seq), size):
        yield seq[i:i + size]

class VectorStore:
    """Manages vector embeddings and performs similarity searches using FAISS."""
    def __init__(
        self,
        embedder: 'EmbeddingProcessor',
        doc_store: DocumentStore,
        data_root: str = "data",
        *,
        batch_size: int = 128,  
        save_every: int = 1,      
    ):
        self.embedder = embedder
        self.doc_store = doc_store
        self.batch_size = max(1, int(batch_size))
        self.save_every = max(1, int(save_every))

        model_name = self.embedder.embedding_model.replace("/", "_")
        self.store_path = os.path.join(data_root, self.doc_store.source_name, model_name)
        os.makedirs(self.store_path, exist_ok=True)

        self.index_file = os.path.join(self.store_path, "vectors.faiss")
        self.ids_file = os.path.join(self.store_path, "indexed_ids.pkl")

        self.indexed_ids: set[int] = set()

        self._load_or_initialize()
        self.sync_with_store()

    def _load_or_initialize(self):
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
        faiss.write_index(self.index, self.index_file)
        with open(self.ids_file, 'wb') as f:
            pickle.dump(self.indexed_ids, f)
        print(f"Saved FAISS index ({self.index.ntotal} vectors) and ID set.")

    def add(self, docs: Union[Document, List[Document]], refresh: bool = False):
        if not isinstance(docs, list):
            docs = [docs]

        self.doc_store.add(docs, refresh=refresh)

        hashed_ids_all = np.array([get_stable_id(doc.id) for doc in docs], dtype='int64')
        if self.index.ntotal > 0 and len(hashed_ids_all):
            self.index.remove_ids(hashed_ids_all)
            self.indexed_ids.difference_update(hashed_ids_all.tolist())

        batch_i = 0
        for chunk in _batched(docs, self.batch_size):
            contents = [d.content_to_embed for d in chunk]
            if not contents:
                continue
            
            embeddings = self.embedder.embed(contents)
            emb_np = np.array(embeddings, dtype='float32')

            ids_np = np.array([get_stable_id(d.id) for d in chunk], dtype='int64')
            self.index.add_with_ids(emb_np, ids_np)
            self.indexed_ids.update(ids_np.tolist())

            batch_i += 1
            if batch_i % self.save_every == 0:
                self._save()

        self._save()

    def sync_with_store(self, refresh: bool = False):
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

            print(f"Re-indexing {len(all_docs)} documents (batch_size={self.batch_size})...")
            batch_i = 0
            for chunk in _batched(all_docs, self.batch_size):
                contents = [d.content_to_embed for d in chunk]
                if not contents:
                    continue

                embeddings = self.embedder.embed(contents)
                emb_np = np.array(embeddings, dtype='float32')
                ids_np = np.array([get_stable_id(d.id) for d in chunk], dtype='int64')

                self.index.add_with_ids(emb_np, ids_np)
                self.indexed_ids.update(ids_np.tolist())

                batch_i += 1
                if batch_i % self.save_every == 0:
                    self._save()
        else:
            all_doc_ids = self.doc_store.get_all_ids()
            docs_to_index = []
            for doc_id in all_doc_ids:
                hid = get_stable_id(doc_id)
                if hid not in self.indexed_ids:
                    doc = self.doc_store.get(doc_id)
                    if doc:
                        docs_to_index.append(doc)

            if not docs_to_index:
                print("VectorStore is already in sync. No new documents to add.")
                return

            print(f"Found {len(docs_to_index)} missing documents. Indexing in batches of {self.batch_size}...")
            self.add(docs_to_index, refresh=False)

        self._save()
        print("Sync complete.")
    
    def query(self, query_text: str, n_results: int = 5, metadata_filter: Optional[Dict[str, Any]] = None):
        """Semantic search via FAISS, with optional metadata pre-filtering.
        
        :param query_text: str, The text to search for.
        :param n_results: int, The maximum number of results to return, defaults to 5
        :param metadata_filter: Optional[Dict[str, Any]], A dictionary of key-value pairs for
                                exact-match metadata filtering before the vector search, defaults to None
        :return: List[{'document': Document, 'distance': float}]
        """
        q_emb = self.embedder.embed(query_text)
        if isinstance(q_emb, list) and q_emb and isinstance(q_emb[0], (list, np.ndarray)):
            q_emb = q_emb[0]
        q_np = np.asarray([q_emb], dtype='float32')

        if self.index.ntotal == 0:
            return []

        search_params = None
        k = int(n_results)
        
        if metadata_filter:
            allowed_doc_ids = self.doc_store.get_doc_ids_by_metadata(metadata_filter)
            
            if not allowed_doc_ids:
                print("No documents match the metadata filter.")
                return []
                
            allowed_hashed_ids = np.array(
                [get_stable_id(doc_id) for doc_id in allowed_doc_ids], 
                dtype='int64'
            )
            
            indexed_allowed_ids = np.intersect1d(
                allowed_hashed_ids, 
                np.array(list(self.indexed_ids), dtype='int64')
            )
            
            if indexed_allowed_ids.size == 0:
                print("No indexed documents match the metadata filter.")
                return []
            
            # pylint: disable=no-value-for-parameter
            selector = faiss.IDSelectorBatch(indexed_allowed_ids)
            
            search_params = faiss.SearchParameters()
            search_params.sel = selector
            k = min(k, indexed_allowed_ids.size)
        
        k = min(k, self.index.ntotal)
        
        if k == 0:
            return []

        distances, hashed_ids = self.index.search(q_np, k, params=search_params)

        all_doc_ids = self.doc_store.get_all_ids()
        id_map = {get_stable_id(doc_id): doc_id for doc_id in all_doc_ids}

        results = []
        for dist, hid in zip(distances[0], hashed_ids[0]):
            if hid == -1:  # FAISS returns -1 for empty slots if k > num_results
                continue
            doc_id = id_map.get(int(hid))
            if not doc_id:
                continue
            doc = self.doc_store.get(doc_id)
            if doc:
                results.append({"document": doc, "distance": float(dist)})
        return results

    def clear(self):
        """Clears the entire VectorStore and its associated DocumentStore.
        
        This deletes all documents, metadata indexes, and vector indexes from disk
        and re-initializes empty stores.
        """
        print(f"Clearing VectorStore at {self.store_path}...")
        self.doc_store.clear()
        
        if os.path.exists(self.index_file):
            os.remove(self.index_file)
        if os.path.exists(self.ids_file):
            os.remove(self.ids_file)
            
        self._load_or_initialize()
        
        print("VectorStore cleared.")