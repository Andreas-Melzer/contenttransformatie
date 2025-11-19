from typing import Dict, List, Optional, Any
from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    """
    Credentials and Client Configuration.
    Does NOT contain paths. Does NOT import paths.
    """
    
    # --- API Keys & Endpoints ---
    azure_api_key: Optional[str] = Field(None, validation_alias="AZURE_OPENAI_API_KEY")
    azure_endpoint: Optional[str] = Field(None, validation_alias="AZURE_OPENAI_ENDPOINT")
    azure_eus2_api_key: Optional[str] = Field(None, validation_alias="AZURE_OPENAI_API_KEY_EUS2")
    azure_eus2_endpoint: Optional[str] = Field(None, validation_alias="AZURE_OPENAI_ENDPOINT_EUS2")
    openrouter_api_key: Optional[str] = Field(None, validation_alias="OPENROUTER_API_KEY")

    azure_subscription_id: Optional[str] = Field(None, validation_alias="AZURE_SUBSCRIPTION_ID")
    azure_resource_group: Optional[str] = Field(None, validation_alias="AZURE_RESOURCE_GROUP")
    azure_workspace_name: Optional[str] = Field(None, validation_alias="AZURE_WORKSPACE")
    mlflow_location: Optional[str] = Field(None, validation_alias="MLFLOW_LOCATION")
    
    azure_storage_account: Optional[str] = Field(None, validation_alias="AZURE_STORAGE_ACCOUNT")
    azure_container_name: Optional[str] = Field(None, validation_alias="AZURE_CONTAINER_NAME")

    clients: Dict[str, Dict[str, Any]] = Field(default_factory=dict, exclude=True)

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
        "text-embedding-qwen3-embedding-4b": "local",
    }

    llm_model: str = "gpt-5-mini"
    embedding_model: str = "text-embedding-3-large"
    raw_doc_store_name: str = "kme_content"

    indexed_metadata_keys: List[str] = [
        "BELASTINGSOORT", "PROCES_ONDERWERP", "PRODUCT_SUBONDERWERP", "km_number"
    ]

    @model_validator(mode='after')
    def build_clients_dictionary(self) -> 'Settings':
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
        self.clients = {name: config for name, config in self.clients.items() if config.get("api_key") or config.get("base_url")}
        return self

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding='utf-8',
        extra="ignore"
    )

# Standard Singleton
settings = Settings()