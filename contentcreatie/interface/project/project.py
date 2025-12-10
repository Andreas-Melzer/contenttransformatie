import uuid
from typing import Dict, Any, List, Optional
import os
import json
from contentcreatie.config.settings import settings
from contentcreatie.config.paths import paths
from utils.debounce import debounce
from contentcreatie.interface.project.project_ledger import project_ledger
from contentcreatie.storage.mount_manager import mount_manager
from contentcreatie.storage.storage_service import storage_service

class Project:
    """
    Encapsulates all data and logic for a single content creation project,
    managing data persistence across separate metadata and data files.
    """

    def __init__(self, vraag: str, subvragen: Optional[List[str]], project_id: Optional[str] = None, belastingsoort: Optional[str] = None, proces_onderwerp: Optional[str] = None, product_subonderwerp: Optional[str] = None):
        self._id: str = project_id or str(uuid.uuid4())
        self._vraag: str = vraag
        self._subvragen: List[str] = subvragen or []
        self._belastingsoort: Optional[str] = belastingsoort
        self._proces_onderwerp: Optional[str] = proces_onderwerp
        self._product_subonderwerp: Optional[str] = product_subonderwerp

        # Default values for Search Data
        self._search_messages: List[Dict[str, Any]] = []
        self._agent_found_documents: Dict[str, Any] = {}
        self._self_found_documents: Dict[str, Any] = {}
        self._scratchpad: List[Dict[str, Any]] = []
        self._selected_doc_id: Optional[str] = None
        
        # Default values for Consolidate Data
        self._consolidate_messages: List[Dict[str, Any]] = []
        self._saved_selection_consolidate: List[str] = []
        self._consolidated_text: str = ""
        self._consolidated_json: Dict = {}
        
        # Default values for Rewrite Data
        self._rewrite_messages: List[Dict[str, Any]] = []
        self._rewritten_text: str = {}
        self._rewritten_json: Dict = {}

    # --- Path Helpers ---
    def _get_path(self, suffix: str = "") -> str:
        """Constructs the file path for project files."""
        return str(paths.projects_folder / f"{self.id}{suffix}.json")
    
    def _get_search_data_path(self) -> str:
        return self._get_path("_search")
    
    def _get_consolidate_data_path(self) -> str:
        return self._get_path("_consolidate")
    
    def _get_rewrite_data_path(self) -> str:
        return self._get_path("_rewrite")

    def get_settings(self):
        return settings
    
    @debounce(0.5)
    def save(self):
        self._perform_save()
        
    def save_immidate(self):
        self._perform_save()
        
    def _perform_save(self):
        """
        Saves the project's metadata and data to separate files.
        Updates the central ledger immediately.
        """
        if not paths.projects_folder.exists():
            paths.projects_folder.mkdir(parents=True, exist_ok=True)
        
        # 1. Save Metadata
        metadata_path = self._get_path()
        metadata = self.to_metadata_dict()
        with open(metadata_path, "w", encoding="utf-8") as f:
            json.dump(metadata, f, indent=4)
            
        # 2. Save Data Chunks
        search_path = self._get_search_data_path()
        with open(search_path, "w", encoding="utf-8") as f:
            json.dump(self.to_search_data_dict(), f, indent=4)
            
        consolidate_path = self._get_consolidate_data_path()
        with open(consolidate_path, "w", encoding="utf-8") as f:
            json.dump(self.to_consolidate_data_dict(), f, indent=4)
            
        rewrite_path = self._get_rewrite_data_path()
        with open(rewrite_path, "w", encoding="utf-8") as f:
            json.dump(self.to_rewrite_data_dict(), f, indent=4)
        
        # 3. Update Ledger
        project_ledger.update_project(metadata)
        
        if paths.remote:

            
            files_to_sync = [
                f"projects/{self.id}.json",
                f"projects/{self.id}_search.json",
                f"projects/{self.id}_consolidate.json",
                f"projects/{self.id}_rewrite.json"
            ]
            
            for blob_path in files_to_sync:
                mount_manager.mount(blob_path)

        print(f"Saved project {self.vraag}")
        
    @classmethod
    def from_id(cls, project_id: str) -> "Project":
        """
        Loads a project from disk. 
        If running in Remote mode, it lazily mounts (downloads) only the necessary files.
        """
        
        # --- Lazy Mount Strategy ---
        if paths.remote:
            try:
                from contentcreatie.storage.mount_manager import mount_manager
                # Mount the 4 specific files required for this project
                # This avoids downloading the entire 'projects' folder
                files_to_mount = [
                    f"projects/{project_id}.json",
                    f"projects/{project_id}_search.json",
                    f"projects/{project_id}_consolidate.json",
                    f"projects/{project_id}_rewrite.json"
                ]
                for f in files_to_mount:
                    mount_manager.mount(f)
            except ImportError:
                print("Warning: Remote set to True but MountManager not found.")

        # --- Standard Load Logic ---
        metadata_path = paths.projects_folder / f"{project_id}.json"

        if not metadata_path.exists():
             raise FileNotFoundError(f"Project metadata not found at {metadata_path}")

        with open(metadata_path, "r", encoding="utf-8") as f:
            metadata = json.load(f)

        project = cls(
            project_id=metadata["id"],
            vraag=metadata["vraag"],
            subvragen=metadata.get("subvragen", []),
            belastingsoort=metadata.get("belastingsoort"),
            proces_onderwerp=metadata.get("proces_onderwerp"),
            product_subonderwerp=metadata.get("product_subonderwerp")
        )
        
        # Load Search Data
        search_path = project._get_search_data_path()
        if os.path.exists(search_path):
            with open(search_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                project._search_messages = data.get("search_messages", [])
                project._agent_found_documents = data.get("agent_found_documents", {})
                project._self_found_documents = data.get("self_found_documents", {})
                project._scratchpad = data.get("scratchpad", [])
                project._selected_doc_id = data.get("selected_doc_id")
        
        # Load Consolidate Data
        consolidate_path = project._get_consolidate_data_path()
        if os.path.exists(consolidate_path):
            with open(consolidate_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                project._consolidate_messages = data.get("consolidate_messages", [])
                project._saved_selection_consolidate = data.get("saved_selection_consolidate", [])
                project._consolidated_text = data.get("consolidated_text", "")
                project._consolidated_json = data.get("consolidated_json", {})
        
        # Load Rewrite Data
        rewrite_path = project._get_rewrite_data_path()
        if os.path.exists(rewrite_path):
            with open(rewrite_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                project._rewrite_messages = data.get("rewrite_messages", [])
                project._rewritten_text = data.get("rewritten_text", "")
                project._rewritten_json = data.get("rewritten_json", {})

        return project
    
    def delete(self):
        """
        Hard delete:
        1. Removes from Ledger (so it disappears from UI).
        2. Unmounts files (stops sync).
        3. Deletes from Blob Storage (permanent data loss).
        4. Cleans up local disk.
        """
        # 1. Remove from Ledger
        project_ledger.delete_project(self.id)

        # List of all associated files
        files_to_remove = [
            (f"projects/{self.id}.json", self._get_path()),
            (f"projects/{self.id}_search.json", self._get_search_data_path()),
            (f"projects/{self.id}_consolidate.json", self._get_consolidate_data_path()),
            (f"projects/{self.id}_rewrite.json", self._get_rewrite_data_path())
        ]
        if paths.remote:
            for blob_name, local_path in files_to_remove:
                # A. Stop tracking (Unmount)
                mount_manager.unmount(blob_name)
                
                # B. Delete directly from Azure
                storage_service.delete_blob(blob_name)
                print(f"Deleted blob: {blob_name}")

        # 3. Local Disk Cleanup
        # We explicitly delete local files to free up space/clean state
        for _, local_path in files_to_remove:
            if os.path.exists(local_path):
                try:
                    os.remove(local_path)
                    print(f"Deleted local file: {local_path}")
                except OSError as e:
                    print(f"Error deleting {local_path}: {e}")
                        
    def reset(self):
            """
            Resets the project to a clean state.
            Wipes all gathered data, found documents, and chat history.
            Preserves metadata (ID, Vraag, Belastingsoort, etc.).
            """
            print(f"Resetting project {self.id} to clean state...")

            # 1. Clear Search Data
            self._search_messages = []
            self._agent_found_documents = {}
            self._self_found_documents = {}
            self._scratchpad = []
            self._selected_doc_id = None
            
            # 2. Clear Consolidate Data
            self._consolidate_messages = []
            self._saved_selection_consolidate = []
            self._consolidated_text = ""
            self._consolidated_json = {}
            
            # 3. Clear Rewrite Data
            self._rewrite_messages = []
            self._rewritten_text = ""
            self._rewritten_json = {}
            
            # 4. Save the "Empty" state to disk/cloud immediately
            # This overwrites the existing files with empty lists/dicts
            self.save()
            
            print("Project reset complete.")
            
    def to_metadata_dict(self) -> Dict[str, Any]:
        return {
            "id": self._id,
            "vraag": self._vraag,
            "subvragen": self._subvragen,
            "belastingsoort": self._belastingsoort,
            "proces_onderwerp": self._proces_onderwerp,
            "product_subonderwerp": self._product_subonderwerp,
        }
        
    def to_search_data_dict(self) -> Dict[str, Any]:
        return {
            "search_messages": self._search_messages,
            "agent_found_documents": self._agent_found_documents,
            "self_found_documents": self._self_found_documents,
            "scratchpad": self._scratchpad,
            "selected_doc_id": self._selected_doc_id,
        }
    
    def to_consolidate_data_dict(self) -> Dict[str, Any]:
        return {
            "consolidate_messages": self._consolidate_messages,
            "consolidated_json" :self._consolidated_json,
            "saved_selection_consolidate": self._saved_selection_consolidate,
            "consolidated_text": self._consolidated_text,
        }
    
    def to_rewrite_data_dict(self) -> Dict[str, Any]:
        return {
            "rewrite_messages": self._rewrite_messages,
            "rewritten_text": self._rewritten_text,
            "rewritten_json" : self._rewritten_json
        }

    # --- Getters and Setters ---
    @property
    def id(self) -> str: return self._id

    @property
    def vraag(self) -> str: return self._vraag
    @vraag.setter
    def vraag(self, value: str): self._vraag = value; self.save()

    @property
    def subvragen(self) -> List[str]: return self._subvragen
    @subvragen.setter
    def subvragen(self, value: List[str]): self._subvragen = value; self.save()

    @property
    def search_messages(self) -> List[Dict[str, Any]]: return self._search_messages
    @search_messages.setter
    def search_messages(self, value: List[Dict[str, Any]]): self._search_messages = value; self.save()
        
    @property
    def consolidate_messages(self) -> List[Dict[str, Any]]: return self._consolidate_messages
    @consolidate_messages.setter
    def consolidate_messages(self, value: List[Dict[str, Any]]): self._consolidate_messages = value; self.save()
        
    @property
    def rewrite_messages(self) -> List[Dict[str, Any]]: return self._rewrite_messages
    @rewrite_messages.setter
    def rewrite_messages(self, value: List[Dict[str, Any]]): self._rewrite_messages = value; self.save()

    @property
    def agent_found_documents(self) -> Dict[str, Any]: return self._agent_found_documents
    @agent_found_documents.setter
    def agent_found_documents(self, value: Dict[str, Any]): self._agent_found_documents = value; self.save()

    @property
    def self_found_documents(self) -> Dict[str, Any]: return self._self_found_documents
    @self_found_documents.setter
    def self_found_documents(self, value: Dict[str, Any]): self._self_found_documents = value; self.save()
        
    @property
    def scratchpad(self) -> List[Dict[str, Any]]: return self._scratchpad
    @scratchpad.setter
    def scratchpad(self, value: List[Dict[str, Any]]): self._scratchpad = value; self.save()
        
    @property
    def saved_selection_consolidate(self) -> List[str]: return self._saved_selection_consolidate
    @saved_selection_consolidate.setter
    def saved_selection_consolidate(self, value: List[str]): self._saved_selection_consolidate = value; self.save()
        
    @property
    def selected_doc_id(self) -> Optional[str]: return self._selected_doc_id
    @selected_doc_id.setter
    def selected_doc_id(self, value: Optional[str]): self._selected_doc_id = value; self.save()
        
    @property
    def found_documents(self): return {**self._self_found_documents, **self._agent_found_documents}

    def upsert_document(self, doc_id, relevance: int = 0):
        if doc_id:
            self._agent_found_documents[doc_id] = relevance
            self.save()
            
    def reset_messages(self):
        self._search_messages.clear()
        self._consolidate_messages.clear()
        self._rewrite_messages.clear()
        self.save()
        
    def reset_search_messages(self):
        self._search_messages.clear(); self.save()
        
    def reset_consolidate_messages(self):
        self._consolidate_messages.clear(); self.save()
        
    def reset_rewrite_messages(self):
        self._rewrite_messages.clear(); self.save()
        
    @property
    def consolidated_text(self) -> str: return self._consolidated_text
    @consolidated_text.setter
    def consolidated_text(self, value: str): self._consolidated_text = value; self.save()
        
    @property
    def consolidated_json(self) -> Dict: return self._consolidated_json
    @consolidated_json.setter
    def consolidated_json(self, value :Dict): self._consolidated_json = value; self.save()
        
    @property
    def rewritten_text(self) -> str: return self._rewritten_text
    @rewritten_text.setter
    def rewritten_text(self, value: str): self._rewritten_text = value; self.save()
        
    @property
    def rewritten_json(self) -> Dict: return self._rewritten_json
    @rewritten_json.setter
    def rewritten_json(self, value: Dict): self._rewritten_json = value; self.save()

    def get_domain_filter(self) -> Dict:
        if self._belastingsoort:
            if self._belastingsoort == "ALLE BELASTINGSOORTEN":
                return {}
            
            return {"BELASTINGSOORT": self._belastingsoort}
        else:
            return None