import hashlib
import os
import pickle
from typing import Any, Dict, List, Optional, Union
import faiss
import numpy as np
from .llm_client import EmbeddingProcessor
from .document_store import DocumentStore
from .document import Document

from logging import getLogger
logger = getLogger("Contenttransformatie")


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
        embedder: EmbeddingProcessor,
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