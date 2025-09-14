import uuid
from typing import Dict, Any, List, Optional
import os
import json
from llm_client.agent import MultiTurnAgent
from config.settings import settings
from interface.utils.debounce import debounce

class Project:
    """
    Encapsulates all data and logic for a single content creation project,
    managing data persistence across separate metadata and data files.
    """

    def __init__(self, vraag: str, subvragen: Optional[List[str]], project_id: Optional[str] = None):
        self._id: str = project_id or str(uuid.uuid4())
        self._vraag: str = vraag
        self._subvragen: List[str] = subvragen or []

        # Default values for data attributes
        self._messages: List[Dict[str, Any]] = [
            {"role": "assistant", "content": f"Oké, ik start het onderzoek voor de vraag: '{vraag}' en subvragen {self._subvragen}. Laten we beginnen."}
        ]
        self._agent_found_documents: Dict[str, Any] = {}
        self._self_found_documents: Dict[str, Any] = {}
        self._scratchpad: List[Dict[str, Any]] = []
        self._saved_selection_consolidate: List[str] = []
        self._selected_doc_id: Optional[str] = None
        
        # Non-persistent attribute
        self.agent: Optional[MultiTurnAgent] = None

    def _get_path(self, suffix: str = "") -> str:
        """Constructs the file path for project files."""
        return os.path.join(settings.projects_data_root, f"{self.id}{suffix}.json")

    @debounce(0.5)
    def save(self):
        """Saves the project's metadata and data to separate files."""
        if not os.path.exists(settings.projects_data_root):
            os.makedirs(settings.projects_data_root)
        
        # Save metadata file ({id}.json)
        with open(self._get_path(), "w", encoding="utf-8") as f:
            json.dump(self.to_metadata_dict(), f, indent=4)
            
        # Save data file ({id}_data.json)
        with open(self._get_path("_data"), "w", encoding="utf-8") as f:
            json.dump(self.to_data_dict(), f, indent=4)
            
        print(f"Saved project {self.vraag}")

    def to_metadata_dict(self) -> Dict[str, Any]:
        """Serializes the project's metadata to a dictionary."""
        return {
            "id": self._id,
            "vraag": self._vraag,
            "subvragen": self._subvragen,
        }
        
    def to_data_dict(self) -> Dict[str, Any]:
        """Serializes the project's dynamic data to a dictionary."""
        return {
            "messages": self._messages,
            "agent_found_documents": self._agent_found_documents,
            "self_found_documents": self._self_found_documents,
            "scratchpad": self._scratchpad,
            "saved_selection_consolidate": self._saved_selection_consolidate,
            "selected_doc_id": self._selected_doc_id,
        }

    @classmethod
    def from_id(cls, project_id: str) -> "Project":
        """Loads a project from its metadata and data files."""
        metadata_path = os.path.join(settings.projects_data_root, f"{project_id}.json")
        data_path = os.path.join(settings.projects_data_root, f"{project_id}_data.json")

        with open(metadata_path, "r", encoding="utf-8") as f:
            metadata = json.load(f)

        project = cls(
            project_id=metadata["id"],
            vraag=metadata["vraag"],
            subvragen=metadata.get("subvragen", [])
        )
        
        if os.path.exists(data_path):
            with open(data_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                project._messages = data.get("messages", project._messages)
                project._agent_found_documents = data.get("agent_found_documents", {})
                project._self_found_documents = data.get("self_found_documents", {})
                project._scratchpad = data.get("scratchpad", [])
                project._saved_selection_consolidate = data.get("saved_selection_consolidate", [])
                project._selected_doc_id = data.get("selected_doc_id")

        return project

    # --- Properties for controlled access and auto-saving ---

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
    def messages(self) -> List[Dict[str, Any]]:
        return self._messages

    @messages.setter
    def messages(self, value: List[Dict[str, Any]]):
        self._messages = value
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
