import os
from pathlib import Path
from typing import Dict, List, Optional

from pydantic import BaseModel, Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class ClientSettings(BaseModel):
    """
    Configuration for a single API client.

    :param api_key: Optional[str], The API key for the client, defaults to None
    :param api_version: Optional[str], The API version string, defaults to "2025-03-01-preview"
    :param azure_endpoint: Optional[str], The endpoint URL for Azure clients, defaults to None
    :param base_url: Optional[str], The base URL for the API endpoint, defaults to None
    """
    api_key: Optional[str] = None
    api_version: Optional[str] = "2025-03-01-preview"
    azure_endpoint: Optional[str] = None
    base_url: Optional[str] = None


class Settings(BaseSettings):
    """
    Main application settings, loaded from an .env file and environment variables.
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

    # --- Client Configurations ---
    clients: Dict[str, ClientSettings] = Field(default_factory=dict, exclude=True)

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
    }

    # --- Default Model Selection ---
    llm_model: str = "gpt-5-mini"
    embedding_model: str = "text-embedding-3-large"

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
        :return: Settings, The validated and updated settings instance.
        """
        self.clients = {
            "azure": ClientSettings(
                api_key=self.azure_api_key,
                azure_endpoint=self.azure_endpoint
            ),
            "azure_eus2": ClientSettings(
                api_key=self.azure_eus2_api_key,
                azure_endpoint=self.azure_eus2_endpoint
            ),
            "openrouter": ClientSettings(
                base_url="https://openrouter.ai/api/v1",
                api_key=self.openrouter_api_key
            ),
            "local": ClientSettings(
                base_url="http://127.0.0.1:1234/v1",
                api_key="not_required"
            )
        }
        return self

    # --- Pydantic Configuration ---
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding='utf-8',
        extra="ignore"
    )


settings = Settings()