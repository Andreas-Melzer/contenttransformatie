import json
import os
import shutil
from dataclasses import asdict
from typing import Any, Dict, List, Optional, Union, Set
import pandas as pd  # Added import
from whoosh.fields import ID, TEXT, Schema
from whoosh.index import create_in, exists_in, open_dir
from whoosh.qparser import MultifieldParser
from .document import Document, SimpleDocument
from config.logger import get_logger

logger = get_logger()
 
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