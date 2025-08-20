from nicegui import ui, app
import uuid
from utils.project_manager import get_project, set_active_project_id
from utils.ui_components import display_document_table, display_document_viewer
from utils.component_loader import load_components
from styles.custom_css import apply_custom_css

# Apply custom CSS
apply_custom_css()

@ui.page('/project/{project_id}')
def search_and_select_page(project_id: str):
    # Set active project
    set_active_project_id(project_id)
    
    # Get the active project
    active_project = get_project(project_id)
    if not active_project:
        with ui.column().classes('items-center justify-center h-screen'):
            ui.label('Selecteer alstublieft een project op het dashboard.').classes('text-red-500 text-xl')
            ui.button('Ga naar Dashboard', on_click=lambda: ui.run_javascript('window.location.href="/"')).classes('mt-4')
        return
    
    # Load components
    agent, doc_store = load_components(active_project)
    
    # Header
    with ui.header().classes('items-center justify-between'):
        with ui.row().classes('items-center'):
            ui.button('← Terug naar Dashboard', on_click=lambda: ui.run_javascript('window.location.href="/"')).classes('mr-4')
            ui.label(f'Project: "{active_project["vraag"]}"').classes('text-xl')
    
    # Main content
    ui.label('Stap 1: Zoeken en Selecteren van Documenten').classes('text-2xl font-bold mt-6 mb-4')
    
    # Chat sidebar
    with ui.splitter().classes('w-full h-96 mt-4') as splitter:
        with splitter.before:
            with ui.column().classes('w-full'):
                ui.label('🤖 Onderzoeksagent').classes('text-lg font-bold')
                ui.label('Stel hier vervolgvragen om relevante documenten te vinden.').classes('text-sm text-gray-500 mb-4')
                
                # Chat container
                chat_container = ui.column().classes('w-full h-64 overflow-y-auto')
                
                # Display existing messages
                for message in active_project["messages"]:
                    if message["role"] == "user":
                        ui.chat_message(message["content"], name='You', sent=True)
                    elif message["role"] == "assistant" and message.get("content"):
                        ui.chat_message(message["content"], name='Agent')
                
                # Scratchpad
                with ui.expansion('Kladblok van de Agent', icon='edit_note').classes('w-full mt-4'):
                    scratchpad = active_project.get("scratchpad", [])
                    if not scratchpad:
                        ui.label('Het kladblok is leeg.').classes('text-gray-500 italic')
                    else:
                        for task in scratchpad:
                            completed = task.get('completed', False)
                            task_text = task.get('task', 'N/A')
                            ui.label(f'{"✅" if completed else "☐"} {task_text}').classes('mb-1')
                
                # Chat input
                with ui.row().classes('w-full mt-4'):
                    chat_input = ui.input(placeholder='Stel uw vraag...').classes('flex-grow')
                    
                    async def send_message():
                        prompt = chat_input.value
                        if prompt:
                            # Add user message
                            active_project["messages"].append({"role": "user", "content": prompt})
                            active_project["selected_doc_id"] = None
                            
                            # Clear input
                            chat_input.value = ''
                            
                            # Add user message to chat
                            ui.chat_message(prompt, name='You', sent=True)
                            
                            # Process with agent
                            with ui.spinner():
                                agent.messages = active_project["messages"]
                                agent.scratchpad = active_project["scratchpad"]
                                final_response = agent.chat(query=prompt, max_tool_turns=15)
                                active_project["messages"].append({"role": "assistant", "content": final_response})
                                active_project["scratchpad"] = agent.scratchpad
                            
                            # Add agent response to chat
                            ui.chat_message(final_response, name='Agent')
                            
                            # Refresh the page to show updated content
                            await ui.run_javascript('location.reload()')
                    
                    ui.button('Send', on_click=send_message).classes('ml-2')
        
        with splitter.after:
            # Document display area
            if not active_project["shortlist"]:
                with ui.column().classes('items-center justify-center h-full'):
                    ui.label('De agent heeft nog geen documenten gevonden. Stel een vraag in de chat om te beginnen.').classes('text-gray-500 text-center')
            elif active_project.get("selected_doc_id"):
                display_document_viewer(doc_store, active_project)
            else:
                ui.label('Gevonden Documenten').classes('text-xl font-bold mb-4')
                display_document_table(doc_store, active_project)

# Make sure to export the page function
__all__ = ['search_and_select_page']