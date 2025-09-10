
import os
from pathlib import Path
from typing import Dict, List, Optional, Any

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Main application settings, loaded from an .env file and environment variables.
    Client configurations are stored as plain dictionaries for flexibility.
    """
    # --- Environment Variable Placeholders ---
    azure_api_key: Optional[str] = Field(None, validation_alias="AZURE_OPENAI_API_KEY")
    azure_endpoint: Optional[str] = Field(None, validation_alias="AZURE_OPENAI_ENDPOINT")
    azure_eus2_api_key: Optional[str] = Field(None, validation_alias="AZURE_OPENAI_API_KEY_EUS2")
    azure_eus2_endpoint: Optional[str] = Field(None, validation_alias="AZURE_OPENAI_ENDPOINT_EUS2")
    openrouter_api_key: Optional[str] = Field(None, validation_alias="OPENROUTER_API_KEY")

    # --- Path Settings ---
    base_dir: Path = Path(__file__).resolve().parent
    data_root: Path = base_dir / "data"
    content_folder: Path = base_dir / ".." / "content"

    # --- Client Configurations (as dictionaries) ---
    clients: Dict[str, Dict[str, Any]] = Field(default_factory=dict, exclude=True)

    # --- Model to Client Mapping ---
    llm_client_map: Dict[str, str] = {
        "gpt-4.1-mini": "azure",
        "gpt-oss-120b": "azure",
        "gpt-5-mini": "azure_eus2",
        "gpt-5": "azure_eus2",
        "openai/gpt-oss-20b": "local",
        "qwen/qwen3-4b-2507": "local",
        "mistralai/devstral-small-2507": "local"
    }
    embedding_client_map: Dict[str, str] = {
        "text-embedding-3-large": "azure",
        "text-embedding-qwen3-embedding-4b" :"local",
        
    }

    # --- Default Model Selection ---
    llm_model: str = "gpt-5-mini"
    embedding_model: str = "text-embedding-qwen3-embedding-4b"

    # --- Document Store Settings ---
    raw_doc_store_name: str = "kme_content"
    summary_doc_store_name: str = "kme_content_summarized"

    # --- Metadata Indexing Settings ---
    indexed_metadata_keys: List[str] = [
        "BELASTINGSOORT", "PROCES_ONDERWERP", "PRODUCT_SUBONDERWERP", "km_number"
    ]
    summary_indexed_metadata_keys: List[str] = [
        "title", "BELASTINGSOORT", "PROCES_ONDERWERP",
        "PRODUCT_SUBONDERWERP", "Tags", "km_number"
    ]

    @model_validator(mode='after')
    def build_clients_dictionary(self) -> 'Settings':
        """
        Constructs the `clients` dictionary from the loaded environment variables.
        """
        self.clients = {
            "azure": {
                "type": "azure",
                "api_key": self.azure_api_key,
                "azure_endpoint": self.azure_endpoint,
                "api_version": "2025-03-01-preview"
            },
            "azure_eus2": {
                "type": "azure",
                "api_key": self.azure_eus2_api_key,
                "azure_endpoint": self.azure_eus2_endpoint,
                "api_version": "2025-03-01-preview"
            },
            "openrouter": {
                "type": "openrouter",
                "base_url": "https://openrouter.ai/api/v1",
                "api_key": self.openrouter_api_key
            },
            "local": {
                "type": "local",
                "base_url": "http://127.0.0.1:1234/v1",
                "api_key": "not_required"
            }
        }
        # Filter out clients with missing essential keys (e.g., api_key)
        self.clients = {name: config for name, config in self.clients.items() if config.get("api_key") or config.get("base_url")}
        return self

    # --- Pydantic Configuration ---
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding='utf-8',
        extra="ignore"
    )

settings = Settings()