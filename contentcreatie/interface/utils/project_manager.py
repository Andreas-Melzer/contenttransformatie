import streamlit as st
import os
import json
from contentcreatie.interface.project import Project
from contentcreatie.config.settings import settings
from contentcreatie.config.paths import paths
import uuid
from contentcreatie.interface.project.project_ledger import project_ledger

def load_project(project_id: str) -> Project | None:
    """Laadt een volledig project op basis van zijn ID."""
    try:
        project = Project.from_id(project_id)
        return project
    except FileNotFoundError:
        return None

def create_project(project_id: str, vraag: str,subvragen = [], belastingsoort:str=None, proces:str=None,product:str=None):
    """Maakt een nieuw project aan, initialiseert de agent, en slaat het op."""
    project = Project(vraag=vraag, subvragen=subvragen, project_id=project_id)
    project._belastingsoort = belastingsoort
    project._proces_onderwerp = proces
    project._product_subonderwerp = product
    project.save_immidate()
    st.session_state.projects[project_id] = project

def get_all_projects():
    """Haalt alle projecten op (metadata only)."""
    return st.session_state.get("projects", {})

def get_active_project() -> Project | None:
    """Haalt het momenteel actieve project op en zorgt ervoor dat het volledig geladen is."""
    active_id = st.session_state.get("active_project_id")
    if not active_id:
        st.error("Selecteer alstublieft een project op het dashboard.")
        if st.button("Ga naar Dashboard"):
            st.switch_page("0_Project_Selectie.py")
        st.stop()
        return None

    project = st.session_state.projects.get(active_id)
    
    # Als het project in session state slechts een preview (dict) is, laad de volledige versie.
    if isinstance(project, dict):
        project = load_project(active_id)
        if project:
            st.session_state.projects[active_id] = project
        else:
            st.error(f"Kon project met ID {active_id} niet laden.")
            st.stop()
            return None

    return project

def load_all_projects():
    """
    Loads project metadata from the Ledger. 
    This is instant (O(1)) compared to iterating all files (O(N)).
    """
    return project_ledger.get_all_projects()

def load_project(project_id: str) -> Project | None:
    """
    Loads a project. If the file is missing (corruption), 
    it attempts to 'Resurrect' it using the data from the Ledger.
    """
    try:
        # Try standard load
        project = Project.from_id(project_id)
        return project
    except FileNotFoundError:
        print(f"Project file missing for {project_id}. Attempting resurrection from Ledger...")
        
        # FETCH FROM LEDGER
        ledger_data = project_ledger.get_all_projects().get(project_id)
        
        if ledger_data:
            # Reconstruct the object using the ledger cache
            project = Project(
                project_id=ledger_data.get("id"),
                vraag=ledger_data.get("vraag"),
                subvragen=ledger_data.get("subvragen", []),
                belastingsoort=ledger_data.get("belastingsoort"),
                proces_onderwerp=ledger_data.get("proces_onderwerp"),
                product_subonderwerp=ledger_data.get("product_subonderwerp")
            )
            # Auto-heal: Save it immediately to restore the physical file
            project.save()
            return project
        else:
            return None

def force_delete_project(project_id: str):
    """
    Deletes a project by ID directly. 
    Does NOT require loading the project object first.
    Useful for corrupted projects that cannot be opened.
    """
    # 1. Remove from Ledger
    project_ledger.delete_project(project_id)

    # 2. Identify files
    # We manually construct paths since we don't have an object instance
    files_to_remove = [
        f"projects/{project_id}.json",
        f"projects/{project_id}_search.json",
        f"projects/{project_id}_consolidate.json",
        f"projects/{project_id}_rewrite.json"
    ]

    # 3. Handle Remote Cleanup (Unmount + Blob Delete)
    if paths.remote:
        try:
            from contentcreatie.storage.mount_manager import mount_manager
            from contentcreatie.storage.storage_service import storage_service
            
            for blob_name in files_to_remove:
                mount_manager.unmount(blob_name)
                storage_service.delete_blob(blob_name)
                print(f"Force deleted remote: {blob_name}")
        except ImportError:
            pass

    # 4. Local Disk Cleanup
    # We guess the local path based on the paths config
    for blob_name in files_to_remove:
        # Assuming standard structure: local_root/projects/filename
        filename = os.path.basename(blob_name)
        local_path = paths.projects_folder / filename
        
        if local_path.exists():
            try:
                os.remove(local_path)
                print(f"Force deleted local: {local_path}")
            except OSError:
                pass