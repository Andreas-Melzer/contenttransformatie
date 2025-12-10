import json
import os
from typing import Dict, Any, Optional
from contentcreatie.config.paths import paths
from contentcreatie.storage.storage_service import storage_service
import json
import os
from typing import Dict, Any
from contentcreatie.config.paths import paths

class ProjectLedger:
    """
    Singleton service that manages the index of all available projects.
    It prevents the need to iterate over thousands of files in Blob Storage.
    """
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ProjectLedger, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True

    def get_all_projects(self) -> Dict[str, Any]:
        """
        Loads the project index from the configured ledger path.

        :return: Dict[str, Any], A dictionary of project metadata keyed by ID.
        """
        # The 'paths' object handles the mounting of this specific file if remote
        ledger_path = paths.projects_ledger
        if not ledger_path.exists():
            return {}

        try:
            with open(ledger_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            return {}

    def update_project(self, project_metadata: Dict[str, Any]):
        """
        Updates or adds a project entry to the ledger and saves immediately.

        :param project_metadata: Dict[str, Any], The metadata dictionary of the project.
        :return: None
        """
        current_data = self.get_all_projects()
        project_id = project_metadata['id']
        
        if current_data.get(project_id) == project_metadata:
            return

        current_data[project_id] = project_metadata
        
        paths.projects_ledger.parent.mkdir(parents=True, exist_ok=True)

        with open(paths.projects_ledger, 'w', encoding='utf-8') as f:
            json.dump(current_data, f, indent=2)
            
    def delete_project(self, project_id: str):
            """
            Removes a project from the ledger and syncs the ledger to disk/cloud.
            """
            current_data = self.get_all_projects()
            
            if project_id in current_data:
                del current_data[project_id]
                
                if not paths.projects_ledger.parent.exists():
                    return

                with open(paths.projects_ledger, 'w', encoding='utf-8') as f:
                    json.dump(current_data, f, indent=2)
                
                print(f"ProjectLedger: Deleted {project_id}")
project_ledger = ProjectLedger()