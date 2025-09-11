import json
from typing import Dict, Any, Optional, Callable, Union
from llm_client.tools.tool_base import ToolBase
from llm_client.document_vector_store import DocumentStore

class TaxnomySearchTool(ToolBase):
    """
    Zoektool die standaard filtert op BELASTINGSOORT en optioneel op
    PROCES_ONDERWERP en PRODUCT_SUBONDERWERP. Bouwt Whoosh-syntax automatisch.
    """

    REQUIRED_FIELD = "BELASTINGSOORT"
    OPTIONAL_FIELDS = ("PROCES_ONDERWERP", "PRODUCT_SUBONDERWERP")

    def __init__(
        self,
        doc_store: DocumentStore,
        on_call: Optional[Callable[[Dict[str, Any]], None]] = None,
        on_result: Optional[Callable[[Dict[str, Any]], Union[str, None]]] = None,
        default_limit: int = 5,
        use_contains_match: bool = True,
    ):
        """
        :param doc_store: DocumentStore met metadata-index
        :param default_limit: standaard aantal resultaten
        :param use_contains_match: True => *term* (bevat); False => term* (prefix)
        """
        super().__init__(on_call=on_call, on_result=on_result)
        self.doc_store = doc_store
        self.indexed_metadata_keys = set(self.doc_store.indexed_metadata_keys or [])
        self.default_limit = default_limit
        self.use_contains_match = use_contains_match

    @property
    def schema(self) -> Dict[str, Any]:
        """Functieschema met expliciete parameters voor de 3 velden."""
        fields_txt = ", ".join(sorted(self.indexed_metadata_keys)) if self.indexed_metadata_keys else "—"
        description = (
            "Zoekt in document-metadata met verplichte BELASTINGSOORT en optionele "
            "PROCES_ONDERWERP en PRODUCT_SUBONDERWERP. Bouwt Whoosh-query automatisch. "
            f"Beschikbare velden in index: {fields_txt}."
        )
        return {
            "type": "function",
            "function": {
                "name": "combined_tax_search",
                "description": description,
                "parameters": {
                    "type": "object",
                    "properties": {
                        "belastingsoort": {
                            "type": "string",
                            "description": "Verplicht. Voorbeeld: 'inkomsten', 'btw', 'vennootschap'."
                        },
                        "proces_onderwerp": {
                            "type": "string",
                            "description": "Optioneel. Voorbeeld: 'aangifte', 'bezwaar', 'teruggaaf'."
                        },
                        "product_subonderwerp": {
                            "type": "string",
                            "description": "Optioneel. Fijner subonderwerp of product-subcategorie."
                        },
                        "limit": {
                            "type": "integer",
                            "description": "Max aantal resultaten (default ingesteld in tool)."
                        }
                    },
                    "required": ["belastingsoort"]
                }
            }
        }


    @staticmethod
    def _escape(value: str) -> str:
        """Escape Whoosh speciale tekens eenvoudig (basis set)."""
        # minimalistische escape zodat wildcards blijven werken
        for ch in ['\\', ':', '"']:
            value = value.replace(ch, f"\\{ch}")
        return value

    def _mk_term(self, field: str, value: Optional[str]) -> Optional[str]:
        """Maak een whoosh term met wildcardstrategie."""
        if not value:
            return None
        v = self._escape(value.strip())
        if not v:
            return None
        if self.use_contains_match:
            # bevat-match
            return f'{field}:*{v}*'
        else:
            # prefix-match
            return f'{field}:{v}*'

    def _build_query(
        self,
        belastingsoort: str,
        proces_onderwerp: Optional[str],
        product_subonderwerp: Optional[str]
    ) -> str:
        missing = [f for f in [self.REQUIRED_FIELD, *self.OPTIONAL_FIELDS] if f not in self.indexed_metadata_keys]
        # We draaien toch door, maar geven een nette waarschuwing terug in resultaat.
        parts = []
        req = self._mk_term(self.REQUIRED_FIELD, belastingsoort)
        if req: parts.append(req)
        opt1 = self._mk_term("PROCES_ONDERWERP", proces_onderwerp)
        if opt1: parts.append(opt1)
        opt2 = self._mk_term("PRODUCT_SUBONDERWERP", product_subonderwerp)
        if opt2: parts.append(opt2)
        # Als iemand lege strings doorgeeft, zorg dat er iig de verplichte term is:
        if not parts:
            parts = [f'{self.REQUIRED_FIELD}:*"*"']  # vangnet, praktisch alles
        return " AND ".join(parts)


    def _execute(
        self,
        belastingsoort: str,
        proces_onderwerp: Optional[str] = None,
        product_subonderwerp: Optional[str] = None,
        limit: Optional[int] = None
    ) -> str:
        """Voert de gecombineerde zoekopdracht uit."""
        if not self.indexed_metadata_keys:
            return "Kan geen metadata-zoekactie uitvoeren: er zijn geen metadata-velden geïndexeerd in dit DocumentStore."

        q = self._build_query(belastingsoort, proces_onderwerp, product_subonderwerp)
        max_results = limit or self.default_limit

        results = self.doc_store.search(query_string=q, limit=max_results)
        if not results:
            return json.dumps({
                "query": q,
                "count": 0,
                "items": []
            }, indent=2, ensure_ascii=False)

        items = [{
            "id": doc.id,
            "title": doc.title,
            "content_snippet": (doc.content[:6000] + " ...") if doc.content else "",
            "metadata": {k: v for k, v in (doc.metadata or {}).items() if k in ['BELASTINGSOORT', 'PROCES_ONDERWERP','PRODUCT_SUBONDERWERP', 'VRAAG']} 
        } for doc in results]

        payload = {
            "query": q,
            "count": len(items),
            "items": items
        }
        return json.dumps(payload, indent=2, ensure_ascii=False)
