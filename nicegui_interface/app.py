import uuid
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from nicegui import ui, app
from utils.project_manager import create_project, get_all_projects, initialize_projects
from styles.custom_css import apply_custom_css
import pages.search_and_select  # Import the search and select page to register it

# Initialize projects
initialize_projects()

# Apply custom CSS
apply_custom_css()

# Set up the main page
@ui.page('/')
def main_page():
    # Header with logo and title
    with ui.header().classes('items-center justify-between'):
        with ui.row().classes('items-center'):
            ui.image('https://www.belastingdienst.nl/bld-assets/bld/rhslogos/bld_logo.svg').classes('w-32')
            ui.label('Content Creatie Dashboard').classes('text-2xl font-bold')
    
    ui.markdown('Beheer hier uw contentgeneratie-projecten. Elk project start met een centrale vraag.').classes('mb-6')
    
    # New Project Creation
    with ui.card().classes('w-full mb-6'):
        ui.label('Nieuw Project Starten').classes('text-xl font-bold mb-4')
        
        with ui.column().classes('w-full'):
            project_question = ui.textarea(
                label='Wat is de centrale vraag voor de nieuwe content?',
                placeholder='Bijvoorbeeld: Hoe werkt de belastingaangifte voor startende ondernemers?'
            ).classes('w-full')
            
            async def create_new_project():
                question = project_question.value
                if question:
                    project_id = str(uuid.uuid4())
                    create_project(project_id, question)
                    project_question.value = ''  # Clear the input
                    ui.notify(f"Project '{question}' succesvol aangemaakt!")
                    # Refresh the project list
                    await ui.run_javascript('location.reload()')
            
            ui.button('Maak Nieuw Project', on_click=create_new_project).classes('self-start')
    
    # Existing Projects Overview
    ui.label('Bestaande Projecten').classes('text-xl font-bold mb-4')
    
    # Container for projects
    projects_container = ui.column().classes('w-full')
    
    # Function to update the projects display
    def update_projects_display():
        projects_container.clear()
        projects = get_all_projects()
        
        if not projects:
            with projects_container:
                ui.label('Er zijn nog geen projecten. Maak hierboven een nieuw project aan om te beginnen.').classes('text-gray-500 italic')
        else:
            for project_id, project_data in projects.items():
                with projects_container:
                    with ui.card().classes('w-full mb-4'):
                        with ui.row().classes('w-full justify-between items-center'):
                            with ui.column():
                                ui.label(project_data["vraag"]).classes('text-lg font-bold')
                                doc_count = len(project_data.get("shortlist", {}))
                                ui.label(f'Geselecteerde documenten: {doc_count}').classes('text-sm text-gray-500')
                            ui.button('Open Project', on_click=lambda pid=project_id: ui.run_javascript(f'window.location.href="/project/{pid}"')).classes('self-start')
    
    # Initial update
    update_projects_display()
    
    # Add a periodic refresh to update the display
    ui.timer(5.0, update_projects_display)

# Run the application
if __name__ in {'__main__', '__mp_main__'}:
    ui.run(title='Content Creatie Dashboard', reload=False, port=8081)