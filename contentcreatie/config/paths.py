from pathlib import Path
from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

class PathSettings(BaseSettings):
    """
    Path configuration. 
    Independent singleton that handles local vs remote path resolution.
    """
    
    remote: bool = Field(False, validation_alias="REMOTE")
    

    base_dir: Path = Path(__file__).resolve().parent.parent
    
    data_root: Path = Field(base_dir / "data", validation_alias="DATA_ROOT")
    
    projects_folder: Path = Field(base_dir / "data" / "projects", validation_alias="PROJECTS_FOLDER")
    content_folder: Path = Field(base_dir / "data" / "content", validation_alias="CONTENT_FOLDER")
    docstore_folder: Path = Field(base_dir / "data" / "docstores", validation_alias="DOCSTORE_FOLDER")

    projects_ledger: Path = Field(base_dir / "data" / "projects" / "projects_ledger.json")
    
    @model_validator(mode='after')
    def configure_mounts(self) -> 'PathSettings':
        """
        If REMOTE is True, lazy-import the mount manager and override paths.
        """
        if self.remote:
            try:
                # Lazy import to avoid circular dependency issues at startup
                from ..storage.mount_manager import mount_manager
                from ..storage.storage_service import storage_service
                
                print("PathSettings: Remote detected. Configuring mounts...")
                
                self.data_root = Path(storage_service.local_base_path)

                self.projects_ledger = Path(mount_manager.mount("projects/projects_ledger.json"))
                self.content_folder = Path(mount_manager.mount("content", is_directory=True,read_only=True))
                self.docstore_folder = Path(mount_manager.mount("docstores", is_directory=True,read_only=True))
                

                self.projects_folder = self.projects_ledger.parent
                
            except ImportError as e:
                print(f"PathSettings Error: REMOTE=True but modules missing: {e}")
                raise e
                
        return self

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding='utf-8',
        extra="ignore"
    )

# Standard Singleton
paths = PathSettings()