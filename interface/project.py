import uuid
from typing import Dict, Any, List, Optional
import os
import json
from llm_client.agent import MultiTurnAgent
from config.settings import settings
from interface.utils.debounce import debounce

class Project:
    """Encapsuleert alle data en logica voor een enkel contentcreatie-project."""

    def __init__(self, vraag: str, subvragen: Optional[List[str]], project_id: Optional[str] = None):
        self._id: str = project_id or str(uuid.uuid4())
        self._vraag: str = vraag
        self._subvragen: List[str] = subvragen
        self._messages: List[Dict[str, Any]] = [
            {"role": "assistant", "content": f"Oké, ik start het onderzoek voor de vraag: '{vraag}' en subvragen {" ".join(subvragen)}. Laten we beginnen."}
        ]
        self._agent_found_documents: Dict[str, Any] = {}
        self._self_found_documents: Dict[str, Any] = {}
        self._search_selected_documents: Dict[str, Any] = {}
        self._selected_documents: List[str] = []
        self._selected_doc_id: Optional[str] = None
        self._scratchpad: List[Dict[str, Any]] = []
        self._consolidated_content: Optional[str] = None
        self._rewritten_content: Optional[str] = None
        self._saved_selection_consolidate: List[str] = []
        self._validated: bool = False
        self.agent: Optional[MultiTurnAgent] = None  # Agent wordt extern geïnitialiseerd
        
    @debounce(0.5)
    def save(self):
        """Slaat de huidige staat van het project op in een JSON-bestand."""
        if not os.path.exists(settings.projects_data_root):
            os.makedirs(settings.projects_data_root)
        project_path = os.path.join(settings.projects_data_root, f"{self.id}.json")
        with open(project_path, "w") as f:
            json.dump(self.to_dict(), f, indent=4)
        print(f"saved project {self.vraag}")

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
    def saved_selection_consolidate(self, value: Optional[List[str]]):
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
    def subvragen(self) -> Optional[List[str]]:
        return self._subvragen
    
    @subvragen.setter
    def subvragen(self,value: Optional[List[str]]) -> Optional[List[str]]:
        self._subvragen = value
        self.save()
        
    @property
    def found_documents(self):
        return {**self._self_found_documents, **self._agent_found_documents}

    def upsert_document(self, doc_id, relevance: int = 0):
        if doc_id:
            self._agent_found_documents[doc_id] = relevance
            self.save()

    def to_dict(self) -> Dict[str, Any]:
        """Serializes the project to a dictionary, excluding the agent."""
        return {
            "id": self._id,
            "vraag": self._vraag,
            "subvragen" :self._subvragen,
            #"messages": self._messages,
            "agent_found_documents": self._agent_found_documents,
            "self_found_documents": self._self_found_documents,
            "search_selected_documents": self._search_selected_documents,
            "selected_documents": self._selected_documents,
            "selected_doc_id": self._selected_doc_id,
            #"scratchpad": self._scratchpad,
            "consolidated_content": self._consolidated_content,
            "rewritten_content": self._rewritten_content,
            "saved_selection_consolidate": self._saved_selection_consolidate,
            "validated": self._validated,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Project":
        """Creates a Project instance from a dictionary."""
        project = cls(vraag=data["vraag"], subvragen=data["subvragen"],project_id=data["id"])
        project._messages = data.get("messages", [])
        project._agent_found_documents = data.get("agent_found_documents", {})
        project._self_found_documents = data.get("self_found_documents", {})
        project._search_selected_documents = data.get("search_selected_documents", {})
        project._selected_documents = data.get("selected_documents", [])
        project._selected_doc_id = data.get("selected_doc_id")
        project._scratchpad = data.get("scratchpad", [])
        project._consolidated_content = data.get("consolidated_content")
        project._rewritten_content = data.get("rewritten_content")
        project._saved_selection_consolidate = data.get("saved_selection_consolidate", [])
        project._validated = data.get("validated", False)
        return project