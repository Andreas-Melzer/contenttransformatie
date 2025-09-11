import streamlit as st
from interface.project import Project
from interface.utils.component_loader import load_heavy_components, initialize_agent_for_project
import os
import json
from  config.settings import settings
import uuid

def load_project(project_id: str) -> Project | None:
    """Laadt een project uit een JSON-bestand."""
    project_path = os.path.join(settings.projects_data_root, f"{project_id}.json")
    if not os.path.exists(project_path):
        return None
    with open(project_path, "r") as f:
        data = json.load(f)
    project = Project.from_dict(data)
    # Re-initialize the non-serializable parts
    llm, _, summary_doc_store,  vector_store = load_heavy_components()
    project.agent = initialize_agent_for_project(project, llm, vector_store,summary_doc_store)
    return project

def create_project(project_id: str, vraag: str):
    """Maakt een nieuw project aan, initialiseert de agent, slaat het op en voegt het toe aan de session state."""
    # Stap 1: Laad de zware, gedeelde componenten (gecached)
    llm, _, summary_doc_store,  vector_store = load_heavy_components()
    project = Project(vraag, project_id)
    project.agent = initialize_agent_for_project(project, llm, vector_store,summary_doc_store)
    project.save() # Save the project to disk
    st.session_state.projects[project_id] = project

def get_all_projects():
    """Haalt alle projecten op."""
    return st.session_state.get("projects", {})

def get_active_project() -> Project | None:
    """Haalt het momenteel actieve project op."""
    active_id = st.session_state.get("active_project_id")
    if active_id and active_id in st.session_state.get("projects", {}):
        return st.session_state.projects[active_id]
    
    st.error("Selecteer alstublieft een project op het dashboard.")
    if st.button("Ga naar Dashboard"):
        st.switch_page("Project_Selectie.py")
    st.stop()
    st.set_page_config(layout="wide")

    return None

def load_all_projects():
    """Laadt alle projecten van schijf."""
    projects = {}
    if not os.path.exists(settings.projects_data_root):
        return projects
    
    existing_project_questions = set()
    
    for filename in os.listdir(settings.projects_data_root):
        if filename.endswith(".json"):
            project_id = filename[:-5]
            project = load_project(project_id)
            if project:
                projects[project_id] = project
                existing_project_questions.add(project.vraag)
                
    if os.path.exists(settings.data_root / "project_list.json"):
        print('loading project configurations from project_list')
        with open(settings.data_root / "project_list.json") as f:
            project_init_list = json.load(f)
            for project_init in project_init_list:
                print(project_init)
                if project_init['question'] not in existing_project_questions:
                    project = Project(project_id=str(uuid.uuid4()),
                                      vraag=project_init['question'],
                                      subvragen=project_init['sub_questions'])
                    projects[project.id] = project
                    project.save()
    return projects