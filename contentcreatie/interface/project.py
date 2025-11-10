import uuid
from typing import Dict, Any, List, Optional
import os
import json
from config.settings import settings
from utils.debounce import debounce

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

        # Default values for data attributes
        self._search_messages: List[Dict[str, Any]] = []
        self._agent_found_documents: Dict[str, Any] = {}
        self._self_found_documents: Dict[str, Any] = {}
        self._scratchpad: List[Dict[str, Any]] = []
        self._saved_selection_consolidate: List[str] = []
        self._selected_doc_id: Optional[str] = None
        
        # Default values for consolidate and rewrite data attributes
        self._consolidate_messages: List[Dict[str, Any]] = []
        self._rewrite_messages: List[Dict[str, Any]] = []
        
        # Attributes to store consolidated and rewritten text
        self._consolidated_text: str = ""
        self._consolidated_json: Dict = {}
        self._rewritten_text: str = {}
        self._rewritten_json: Dict = {}
        

    def _get_path(self, suffix: str = "") -> str:
        """Constructs the file path for project files."""
        return os.path.join(settings.projects_folder, f"{self.id}{suffix}.json")
    
    def _get_search_data_path(self) -> str:
        """Constructs the file path for search step data."""
        return self._get_path("_search")
    
    def _get_consolidate_data_path(self) -> str:
        """Constructs the file path for consolidate step data."""
        return self._get_path("_consolidate")
    
    def _get_rewrite_data_path(self) -> str:
        """Constructs the file path for rewrite step data."""
        return self._get_path("_rewrite")

    def get_settings(self):
        return settings
    
    @debounce(0.5)
    def save(self):
        """Saves the project's metadata and data to separate files."""
        if not os.path.exists(settings.projects_folder):
            os.makedirs(settings.projects_folder,exist_ok=True)
        
        with open(self._get_path(), "w", encoding="utf-8") as f:
            json.dump(self.to_metadata_dict(), f, indent=4)
            
        with open(self._get_search_data_path(), "w", encoding="utf-8") as f:
            json.dump(self.to_search_data_dict(), f, indent=4)
            
        with open(self._get_consolidate_data_path(), "w", encoding="utf-8") as f:
            json.dump(self.to_consolidate_data_dict(), f, indent=4)
            
        with open(self._get_rewrite_data_path(), "w", encoding="utf-8") as f:
            json.dump(self.to_rewrite_data_dict(), f, indent=4)
            
        print(f"Saved project {self.vraag}")

    def to_metadata_dict(self) -> Dict[str, Any]:
        """Serializes the project's metadata to a dictionary."""
        return {
            "id": self._id,
            "vraag": self._vraag,
            "subvragen": self._subvragen,
            "belastingsoort": self._belastingsoort,
            "proces_onderwerp": self._proces_onderwerp,
            "product_subonderwerp": self._product_subonderwerp,
        }
        
    def to_search_data_dict(self) -> Dict[str, Any]:
        """Serializes the project's search step data to a dictionary."""
        return {
            "search_messages": self._search_messages,
            "agent_found_documents": self._agent_found_documents,
            "self_found_documents": self._self_found_documents,
            "scratchpad": self._scratchpad,
            "selected_doc_id": self._selected_doc_id,
        }
    
    def to_consolidate_data_dict(self) -> Dict[str, Any]:
        """Serializes the project's consolidate step data to a dictionary."""
        return {
            "consolidate_messages": self._consolidate_messages,
            "consolidated_json" :self._consolidated_json,
            "saved_selection_consolidate": self._saved_selection_consolidate,
            "consolidated_text": self._consolidated_text,
        }
    
    def to_rewrite_data_dict(self) -> Dict[str, Any]:
        """Serializes the project's rewrite step data to a dictionary."""
        return {
            "rewrite_messages": self._rewrite_messages,
            "rewritten_text": self._rewritten_text,
            "rewritten_json" : self._rewritten_json
        }

    @classmethod
    def from_id(cls, project_id: str) -> "Project":
        """Loads a project from its metadata and data files."""
        metadata_path = os.path.join(settings.projects_folder, f"{project_id}.json")
        data_path = os.path.join(settings.projects_folder, f"{project_id}_data.json")

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
        
        # Load search step data if it exists
        search_data_path = project._get_search_data_path()
        if os.path.exists(search_data_path):
            with open(search_data_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                project._search_messages = data.get("messages", project._search_messages)
                project._agent_found_documents = data.get("agent_found_documents", {})
                project._self_found_documents = data.get("self_found_documents", {})
                project._scratchpad = data.get("scratchpad", [])
                project._selected_doc_id = data.get("selected_doc_id")
        
        # Load consolidate step data if it exists
        consolidate_data_path = project._get_consolidate_data_path()
        if os.path.exists(consolidate_data_path):
            with open(consolidate_data_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                project._consolidate_messages = data.get("consolidate_messages", project._consolidate_messages)
                project._saved_selection_consolidate = data.get("saved_selection_consolidate", [])
                project._consolidated_text = data.get("consolidated_text", "")
                project._consolidated_json = data.get("consolidated_json", {})
        
        # Load rewrite step data if it exists
        rewrite_data_path = project._get_rewrite_data_path()
        if os.path.exists(rewrite_data_path):
            with open(rewrite_data_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                project._rewrite_messages = data.get("rewrite_messages", project._rewrite_messages)
                project._rewritten_text = data.get("rewritten_text", "")
                project._rewritten_json = data.get("rewritten_json","")

        return project

    @property
    def id(self) -> str:
        return self._id

    @property
    def vraag(self) -> str:
        return self._vraag
    
    @vraag.setter
    def vraag(self, value: str):
        self._vraag = value
        self.save()

    @property
    def subvragen(self) -> List[str]:
        return self._subvragen

    @subvragen.setter
    def subvragen(self, value: List[str]):
        self._subvragen = value
        self.save()

    @property
    def search_messages(self) -> List[Dict[str, Any]]:
        return self._search_messages

    @search_messages.setter
    def search_messages(self, value: List[Dict[str, Any]]):
        self._search_messages = value
        self.save()
        
    @property
    def consolidate_messages(self) -> List[Dict[str, Any]]:
        return self._consolidate_messages

    @consolidate_messages.setter
    def consolidate_messages(self, value: List[Dict[str, Any]]):
        self._consolidate_messages = value
        self.save()
        
    @property
    def rewrite_messages(self) -> List[Dict[str, Any]]:
        return self._rewrite_messages

    @rewrite_messages.setter
    def rewrite_messages(self, value: List[Dict[str, Any]]):
        self._rewrite_messages = value
        self.save()

    @property
    def agent_found_documents(self) -> Dict[str, Any]:
        return self._agent_found_documents
    
    @agent_found_documents.setter
    def agent_found_documents(self, value: Dict[str, Any]):
        self._agent_found_documents = value
        self.save()

    @property
    def self_found_documents(self) -> Dict[str, Any]:
        return self._self_found_documents

    @self_found_documents.setter
    def self_found_documents(self, value: Dict[str, Any]):
        self._self_found_documents = value
        self.save()
        
    @property
    def scratchpad(self) -> List[Dict[str, Any]]:
        return self._scratchpad

    @scratchpad.setter
    def scratchpad(self, value: List[Dict[str, Any]]):
        self._scratchpad = value
        self.save()
        
    @property
    def saved_selection_consolidate(self) -> List[str]:
        return self._saved_selection_consolidate
    
    @saved_selection_consolidate.setter
    def saved_selection_consolidate(self, value: List[str]):
        self._saved_selection_consolidate = value
        self.save()
        
    @property
    def selected_doc_id(self) -> Optional[str]:
        return self._selected_doc_id
        
    @selected_doc_id.setter
    def selected_doc_id(self, value: Optional[str]):
        self._selected_doc_id = value
        self.save()
        
    @property
    def found_documents(self):
        return {**self._self_found_documents, **self._agent_found_documents}

    def upsert_document(self, doc_id, relevance: int = 0):
        if doc_id:
            self._agent_found_documents[doc_id] = relevance
            self.save()
            
    def reset_messages(self):
        """Reset all message histories for the project."""
        self._search_messages.clear()
        self._consolidate_messages.clear()
        self._rewrite_messages.clear()
        self.save()
        
    def reset_search_messages(self):
        """Reset message history for the search agent."""
        self._search_messages.clear()
        self.save()
        
    def reset_consolidate_messages(self):
        """Reset message history for the consolidate agent."""
        self._consolidate_messages.clear()
        self.save()
        
    def reset_rewrite_messages(self):
        """Reset message history for the rewrite agent."""
        self._rewrite_messages.clear()
        self.save()
        
        
    
    @property
    def consolidated_text(self) -> str:
        return self._consolidated_text
    
    @consolidated_text.setter
    def consolidated_text(self, value: str):
        self._consolidated_text = value
        self.save()
        
    @property
    def consolidated_json(self) -> Dict:
        return self._consolidated_json
    
    @consolidated_json.setter
    def consolidated_json(self, value :Dict):
        self._consolidated_json = value
        self.save()
        
    @property
    def rewritten_text(self) -> str:
        return self._rewritten_text
    
    @rewritten_text.setter
    def rewritten_text(self, value: str):
        self._rewritten_text = value
        self.save()
        
    @property
    def rewritten_json(self) -> Dict:
        return self._rewritten_json
    
    @rewritten_json.setter
    def rewritten_json(self, value: Dict):
        self._rewritten_json = value
        self.save()

    def get_domain_filter(self) -> Dict:
        if self._belastingsoort != '':
            return {"BELASTINGSOORT": self._belastingsoort}
        else:
            return None