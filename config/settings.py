import os
import sys
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings
from typing import Dict, List, Optional
from dotenv import dotenv_values

class ClientSettings(BaseModel):
    """Configuration for a single API client."""
    api_key: Optional[str] = None
    api_version: Optional[str] = "2025-03-01-preview"
    azure_endpoint: Optional[str] = None
    base_url: Optional[str] = None

class Settings(BaseSettings):
    """Main application settings."""
    # --- General ---
    data_root: str = "data"
    content_folder: str = "content"

    # --- Client Configurations ---
    clients: Dict[str, ClientSettings] = {
        "azure": ClientSettings(),
        "azure_eus2": ClientSettings(),
        "openrouter": ClientSettings(base_url="https://openrouter.ai/api/v1"),
        "local": ClientSettings(base_url="http://127.0.0.1:8188/v1", api_key="not_required")
    }

    # --- Model to Client Mapping ---
    llm_client_map: Dict[str, str] = {
        "gpt-4.1-mini": "azure",
        "gpt-oss-120b": "azure",
        "gpt-5-mini": "azure_eus2",
        "gpt-5": "azure_eus2",
        "local": "local"
    }
    embedding_client_map: Dict[str, str] = {
        "text-embedding-3-large": "azure",
    }

    # --- Default Models ---
    llm_model: str = "gpt-4.1-mini"
    embedding_model: str = "text-embedding-3-large"

    # --- Document Stores ---
    raw_doc_store_name: str = "kme_content"
    summary_doc_store_name: str = "kme_content_summarized"
    indexed_metadata_keys: List[str] = ["BELASTINGSOORT", "PROCES_ONDERWERP", "PRODUCT_SUBONDERWERP", "km_number"]
    summary_indexed_metadata_keys: List[str] = ["title", "BELASTINGSOORT", "PROCES_ONDERWERP", "PRODUCT_SUBONDERWERP", "Tags", "km_number"]

    class Config:
        env_file = ".env"
        extra = "ignore"

settings = Settings()

# --- Load environment variables into the client settings ---
# Try to find the .env file in different locations
env_file_paths = [
    ".env",
    "../.env",
    "../../.env",
    os.path.join(os.path.dirname(__file__), "..", ".env"),
    os.path.join(os.path.dirname(__file__), "..", "..", ".env")
]

config = {}
for path in env_file_paths:
    if os.path.exists(path):
        print(f"Loading .env file from: {path}")
        config = dotenv_values(path)
        break
    else:
        print(f".env file not found at: {path}")

if not config:
    print("Warning: No .env file found. Using default settings.")

if config.get("AZURE_OPENAI_API_KEY"):
    settings.clients["azure"].api_key = config["AZURE_OPENAI_API_KEY"]
if config.get("AZURE_OPENAI_ENDPOINT"):
    settings.clients["azure"].azure_endpoint = config["AZURE_OPENAI_ENDPOINT"]
if config.get("AZURE_OPENAI_API_KEY_EUS2"):
    settings.clients["azure_eus2"].api_key = config["AZURE_OPENAI_API_KEY_EUS2"]
if config.get("AZURE_OPENAI_ENDPOINT_EUS2"):
    settings.clients["azure_eus2"].azure_endpoint = config["AZURE_OPENAI_ENDPOINT_EUS2"]
if config.get("OPENROUTER_API_KEY"):
    settings.clients["openrouter"].api_key = config["OPENROUTER_API_KEY"]