from typing import Dict, Any, Optional, Callable, Union, List
from contentcreatie.llm_client.tools.tool_base import ToolBase
from project import Project

class SaveConsolidatedJsonTool(ToolBase):
    """
    A tool that allows the agent to save consolidated JSON content to a project file.
    """
    def __init__(
        self,
        project:Project,
        on_call: Optional[Callable[[Dict[str, Any]], None]] = None,
        on_result: Optional[Callable[[Dict[str, Any]], Union[str, None]]] = None,

    ):
        """Initializes the tool, passing callbacks to the base class.
        :param on_call: Optional[Callable[[Dict[str, Any]], None]], Callback function to be executed when the tool is called, defaults to None
        :param on_result: Optional[Callable[[Dict[str, Any]], Union[str, None]]], Callback function to be executed with the result of the tool, defaults to None
        """
        self.project = project
        super().__init__(on_call=on_call, on_result=on_result)

    @property
    def schema(self) -> Dict[str, Any]:
        """Defines the schema for the save consolidated JSON tool.
        :return: Dict[str, Any], The JSON schema definition for the tool.
        """
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
                        "hoofdvraag": {
                            "type": "string",
                            "description": "De hoofdvraag van het project."
                        },
                        "consolidatie": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "vraag": {"type": "string"},
                                    "publieke_informatie": fragment_schema,
                                    "interne_informatie": fragment_schema
                                },
                                "required": ["vraag", "publieke_informatie", "interne_informatie"]
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
                                "required": ["vraag", "publieke_informatie", "interne_informatie"]
                            }
                        },
                        "gedetecteerde_conflicten": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "conflict_beschrijving": {"type": "string"},
                                    "bron_km": {
                                        "type": "array",
                                        "items": {"type": "string"}
                                    }
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
                    "required": [
                        "hoofdvraag",
                        "consolidatie",
                        "subvragen_consolidatie",
                        "gedetecteerde_conflicten",
                        "informatie_hiaten"
                    ]
                }
            }
        }

    def _execute(self, hoofdvraag: str, consolidatie: List, subvragen_consolidatie: List, gedetecteerde_conflicten: List, informatie_hiaten: List) -> str:
        """Updates the active project's consolidated JSON content and saves it.
        :param hoofdvraag: str, The main question of the project.
        :param consolidatie: List, The consolidated information related to the main question.
        :param subvragen_consolidatie: List, The consolidated information related to the sub-questions.
        :param gedetecteerde_conflicten: List, A list of detected conflicts in the information.
        :param informatie_hiaten: List, A list of identified information gaps.
        :return: str, A confirmation or error message.
        """
        try:

            consolidated_data = {
                "hoofdvraag": hoofdvraag,
                "consolidatie": consolidatie,
                "subvragen_consolidatie": subvragen_consolidatie,
                "gedetecteerde_conflicten": gedetecteerde_conflicten,
                "informatie_hiaten": informatie_hiaten
            }
            
            self.project.consolidated_json = consolidated_data
            
            return f"Consolidated JSON content for project {self.project} updated and saved successfully."
        except Exception as e:
            return f"Error updating consolidated JSON content for project {self.project}: {e}"