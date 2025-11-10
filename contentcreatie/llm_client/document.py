from abc import ABC
from dataclasses import dataclass
from typing import Any, Dict

@dataclass
class Document(ABC):
    """An abstract base class for a document.

    :param id: str, The unique identifier for the document.
    :param title: str, The title of the document.
    :param content: str, The main text content of the document.
    :param metadata: Dict[str, Any], A dictionary for any additional metadata.
    """
    id: str
    title: str
    content: str
    metadata: Dict[str, Any]

    @property
    def content_to_embed(self) -> str:
        """The string content that will be used for generating embeddings.
        
        This can be overridden by subclasses to create more sophisticated embeddings,
        for example, by combining the title and content.

        :return: str, The text to be embedded.
        """
        return self.content
    
@dataclass
class SimpleDocument(Document):
    """A basic, concrete implementation of the Document class."""
    pass
