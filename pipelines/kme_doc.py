from contentcreatie.llm_client.document import (
    Document,
)
from dataclasses import dataclass

@dataclass
class KMEDocument(Document):
    """A document that combines its title and content for embedding."""
    
    @property
    def content_to_embed(self) -> str:
        """Overrides the base property to combine title and content.

        :return: str, The combined title and content for embedding.
        """
        return f"Title: {self.title}\n\nBelastingsoort: {self.metadata['BELASTINGSOORT']}| Proces: {self.metadata['PROCES_ONDERWERP']}| Product: {self.metadata['PRODUCT_SUBONDERWERP']} \n\n{self.metadata.get('summary',"")} \n\n {self.metadata.get('tags',"")}"
    
    @property
    def doorverwijs_artikel(self) -> bool:
        if('linkartikel' in self.metadata['Tags']):
            return True
        else:
            return False