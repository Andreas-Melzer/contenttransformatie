from typing import Dict, Any, Optional, Callable, Union, List
from contentcreatie.llm_client.tools.tool_base import ToolBase
from project import Project

class SaveConsolidatedJsonTool(ToolBase):
    """
    A tool that allows the agent to save consolidated JSON content to a project file.
    """
    def __init__(
        self,
        project: Project,
        on_call: Optional[Callable[[Dict[str, Any]], None]] = None,
        on_result: Optional[Callable[[Dict[str, Any]], Union[str, None]]] = None,
    ):
        self.project = project
        super().__init__(on_call=on_call, on_result=on_result)

    @property
    def schema(self) -> Dict[str, Any]:
        fragment_schema = {
            "type": "object",
            "properties": {
                "fragmenten": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "tekst_fragment": {"type": "string"},
                            "bron_km": {"type": "string"}
                        },
                        "required": ["tekst_fragment", "bron_km"]
                    }
                }
            },
            "required": ["fragmenten"]
        }

        return {
            "type": "function",
            "function": {
                "name": "save_consolidated_json",
                "description": "Use this tool to save consolidated JSON content for a specific project.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "hoofdvraag": {"type": "string"},
                        "consolidatie": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "vraag": {"type": "string"},
                                    "publieke_informatie": fragment_schema,
                                    "interne_informatie": fragment_schema
                                },
                                "required": ["vraag", "publieke_informatie"]
                            }
                        },
                        "subvragen_consolidatie": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "vraag": {"type": "string"},
                                    "publieke_informatie": fragment_schema,
                                    "interne_informatie": fragment_schema
                                },
                                "required": ["vraag", "publieke_informatie"]
                            }
                        },
                        "gedetecteerde_conflicten": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "conflict_beschrijving": {"type": "string"},
                                    "bron_km": {"type": "array", "items": {"type": "string"}}
                                },
                                "required": ["conflict_beschrijving", "bron_km"]
                            }
                        },
                        "informatie_hiaten": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "hiaat_beschrijving": {"type": "string"},
                                    "relevante_vraag": {"type": "string"}
                                },
                                "required": ["hiaat_beschrijving", "relevante_vraag"]
                            }
                        }
                    },
                    "required": ["hoofdvraag", "consolidatie"]
                }
            }
        }

    def _execute(
        self, 
        hoofdvraag: str, 
        consolidatie: List, 
        subvragen_consolidatie: List = None, 
        gedetecteerde_conflicten: List = None, 
        informatie_hiaten: List = None
    ) -> str:
        try:
            # Helper to ensure interne_informatie exists in list items
            def normalize_items(items):
                if not items: return []
                for item in items:
                    if "interne_informatie" not in item:
                        item["interne_informatie"] = {"fragmenten": []}
                return items

            consolidated_data = {
                "hoofdvraag": hoofdvraag,
                "consolidatie": normalize_items(consolidatie),
                "subvragen_consolidatie": normalize_items(subvragen_consolidatie),
                "gedetecteerde_conflicten": gedetecteerde_conflicten or [],
                "informatie_hiaten": informatie_hiaten or []
            }
            
            self.project.consolidated_json = consolidated_data
            return "Consolidated JSON content updated successfully."
        except Exception as e:
            return f"Error updating consolidated JSON content: {e}"