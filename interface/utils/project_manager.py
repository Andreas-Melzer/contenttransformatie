import streamlit as st
from interface.project import Project
from interface.utils.component_loader import load_heavy_components, initialize_agent_for_project, initialize_consolidate_agent_for_project, initialize_rewrite_agent_for_project
import os
import json
from  config.settings import settings
import uuid

def load_project(project_id: str) -> Project | None:
    """Laadt een volledig project op basis van zijn ID."""
    try:
        project = Project.from_id(project_id)
        llm, doc_store, vector_store = load_heavy_components()
        project.agent = initialize_agent_for_project(project, llm, vector_store, doc_store)
        project.consolidate_agent = initialize_consolidate_agent_for_project(project, llm, vector_store, doc_store)
        project.rewrite_agent = initialize_rewrite_agent_for_project(project, llm, vector_store, doc_store)
        return project
    except FileNotFoundError:
        return None

def create_project(project_id: str, vraag: str):
    """Maakt een nieuw project aan, initialiseert de agent, en slaat het op."""
    llm, doc_store, vector_store = load_heavy_components()
    project = Project(vraag=vraag, subvragen=[], project_id=project_id)
    project.agent = initialize_agent_for_project(project, llm, vector_store, doc_store)
    project.consolidate_agent = initialize_consolidate_agent_for_project(project, llm, vector_store, doc_store)
    project.rewrite_agent = initialize_rewrite_agent_for_project(project, llm, vector_store, doc_store)
    project.save()
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
    """Laadt de metadata van alle projecten van schijf voor een snelle lijstweergave."""
    projects = {}
    if not os.path.exists(settings.projects_folder):
        os.makedirs(settings.projects_folder)
    
    existing_project_questions = set()

    # Laad bestaande projecten door metadata-bestanden te lezen
    for filename in os.listdir(settings.projects_folder):
        if filename.endswith(".json") and not filename.endswith("_data.json") and not filename.endswith("_search.json") and not filename.endswith("_consolidate.json") and not filename.endswith("_rewrite.json"):
            project_id = filename[:-5]
            try:
                with open(os.path.join(settings.projects_folder, filename), "r", encoding="utf-8") as f:
                    metadata = json.load(f)
                    projects[project_id] = metadata
                    existing_project_questions.add(metadata['vraag'])
            except (json.JSONDecodeError, KeyError):
                print(f"Skipping corrupt metadata file: {filename}")
                continue

    #TODO dit moet echt ergens anders gebeuren
    # Synchroniseer met de initiële projectenlijst
    project_list_path = os.path.join(settings.data_root, "project_list.json")
    if os.path.exists(project_list_path):
        with open(project_list_path, "r", encoding="utf-8") as f:
            project_init_list = json.load(f)
            for project_init in project_init_list:
                if project_init['question'] not in existing_project_questions:
                    new_project = Project(
                        project_id=str(uuid.uuid4()),
                        vraag=project_init['question'],
                        subvragen=project_init['sub_questions'],
                        belastingsoort=project_init.get('belastingsoort', ''),
                        proces_onderwerp=project_init.get('proces_onderwerp', ''),
                        product_subonderwerp=project_init.get('product_subonderwerp', '')
                    )
                    new_project.save()
                    projects[new_project.id] = new_project.to_metadata_dict()
    
    return projects
