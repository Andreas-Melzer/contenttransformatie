import uuid
from typing import Dict, Any, List, Optional
from llm_client.agent import MultiTurnAgent

class Project:
    """Encapsuleert alle data en logica voor een enkel contentcreatie-project."""
    def __init__(self, vraag: str, project_id: Optional[str] = None):
        self.id: str = project_id or str(uuid.uuid4())
        self.vraag: str = vraag
        self.messages: List[Dict[str, Any]] = [
            {"role": "assistant", "content": f"Oké, ik start het onderzoek voor de vraag: '{vraag}'. Laten we beginnen."}
        ]
        
        #Stap 1 zoeken en selecteren
        self.agent_found_documents: Dict[str, Any] = {}
        self.self_found_documents: Dict[str,Any] = {}
        self.search_selected_documents: Dict[str, Any] = {}
        
        self.selected_documents =[]
        #self.shortlist: Dict[str, Any] = {}
        self.selected_doc_id: Optional[str] = None
        self.scratchpad: List[Dict[str, Any]] = []
        self.consolidated_content: Optional[str] = None
        self.rewritten_content: Optional[str] = None
        self.saved_selection_consolidate: List[str] = []
        self.validated: bool = False
        self.agent: Optional[MultiTurnAgent] = None # Agent wordt extern geïnitialiseerd
        
    @property
    def found_documents(self):
        return self.self_found_documents.update(self.agent_found_documents)
    def upsert_document(self,doc_id, relevance:int = 0):
        if doc_id:
            self.agent_found_documents[doc_id] =relevance 
    