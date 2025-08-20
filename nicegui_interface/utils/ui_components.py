from nicegui import ui
from typing import Dict, Any, List, Optional

def display_document_viewer(doc_store, project: dict):
    """Rendert de detailweergave voor een geselecteerd document binnen een project."""
    doc_id = project["selected_doc_id"]
    
    with ui.column().classes('document-viewer w-full'):
        docs = doc_store.search(f"km_number:{doc_id}")
        doc = docs[0] if docs else None
        
        if doc:
            ui.label(doc.title).classes('text-2xl font-bold')
            
            # Display metadata
            with ui.row().classes('flex-wrap'):
                for key, value in doc.metadata.items():
                    if value and key != 'full_text':
                        ui.label(f'{key.replace("_", " ").title()}: {value}').classes('metadata-chip')
            
            ui.separator()
            
            # Display content
            ui.markdown(doc.content).classes('w-full')
            
            async def close_document():
                project["selected_doc_id"] = None
                await ui.run_javascript('location.reload()')
            
            ui.button('Sluit Document', on_click=close_document).classes('mt-4')
        else:
            ui.label(f'Document met ID {doc_id} niet gevonden.').classes('text-red-500')

def display_document_table(doc_store, project: dict):
    """Versie met directe state updates en bredere layout."""
    docs_list = []
    for doc_id, shortlist_info in project["shortlist"].items():
        docs = doc_store.search(f"km_number:{doc_id}")
        if docs:
            doc = docs[0]
            docs_list.append({
                'id': doc_id,
                'doc': doc,
                'relevance': shortlist_info.get('relevance')
            })
    
    # Sorteer op relevantie
    def get_relevance_score(item):
        try:
            relevance = item.get('relevance')
            if relevance and relevance != '...':
                return float(relevance)
        except (ValueError, TypeError):
            pass
        return -1
    
    docs_list.sort(key=get_relevance_score, reverse=True)
    
    # Control Panel
    with ui.card().classes('w-full mb-4'):
        with ui.row().classes('w-full justify-between items-center'):
            with ui.row():
                async def select_all():
                    # In a real implementation, this would update the selection state
                    ui.notify('Alle documenten geselecteerd')
                    await ui.run_javascript('location.reload()')
                
                async def deselect_all():
                    # In a real implementation, this would update the selection state
                    ui.notify('Alle documenten gedeselecteerd')
                    await ui.run_javascript('location.reload()')
                
                ui.button('✓ Alle', on_click=select_all).classes('mr-2')
                ui.button('✗ Geen', on_click=deselect_all).classes('mr-4')
                
                async def delete_selection():
                    # In a real implementation, this would delete selected documents
                    ui.notify('Selectie verwijderd')
                    await ui.run_javascript('location.reload()')
                
                async def save_selection():
                    # In a real implementation, this would save selected documents
                    ui.notify('Selectie opgeslagen')
                    await ui.run_javascript('location.reload()')
                
                ui.button('🗑️ Verwijder selectie', on_click=delete_selection).classes('mr-2')
                ui.button('💾 Bewaar voor volgende stap', on_click=save_selection, color='primary')
            
            with ui.row():
                ui.label(f'Totaal: {len(docs_list)}').classes('mr-4')
                ui.label(f'Selectie: 0').classes('mr-4')  # In a real implementation, this would show actual selection count
    
    # Document list
    for item in docs_list:
        doc = item['doc']
        doc_id = item['id']
        meta = doc.metadata
        relevance = item.get('relevance', '...')
        if relevance is None:
            relevance = '...'
        
        with ui.card().classes('w-full mb-4'):
            # Header row
            with ui.row().classes('w-full justify-between items-center'):
                with ui.row().classes('items-center'):
                    ui.checkbox(f'Select').classes('mr-4')
                    ui.label(meta.get('km_number', 'N/A')).classes('font-bold mr-4')
                    vraag = meta.get('VRAAG', 'N/A')
                    ui.label(vraag[:200] + "..." if len(vraag) > 200 else vraag).classes('mr-4')
                
                with ui.row().classes('items-center'):
                    ui.label(meta.get('BELASTINGSOORT', 'N/A')).classes('text-sm text-gray-500 mr-4')
                    ui.label(meta.get('PROCES_ONDERWERP', 'N/A')).classes('text-sm text-gray-500 mr-4')
                    
                    if relevance != '...':
                        try:
                            score = float(relevance)
                            color = "text-green-500" if score > 7 else "text-yellow-500" if score > 4 else "text-red-500"
                            ui.label(f'{relevance}').classes(f'font-bold {color}')
                        except:
                            ui.label(f'{relevance}').classes('font-bold')
                    else:
                        ui.label('...').classes('font-bold')
            
            # Expandable detail section
            with ui.expansion('📄 Bekijk volledig antwoord', icon='description').classes('w-full'):
                with ui.card().classes('w-full'):
                    # Info header
                    with ui.row().classes('w-full'):
                        ui.label(f'KM Nummer: {meta.get("km_number", "N/A")}').classes('mr-4')
                        ui.label(f'Product: {meta.get("PRODUCT_SUBONDERWERP", "N/A")}').classes('mr-4')
                        ui.label(f'Relevantie Score: {relevance}').classes('mr-4')
                    
                    ui.separator()
                    
                    # Vraag
                    ui.label('Vraag').classes('text-lg font-bold mt-2')
                    ui.label(meta.get('VRAAG', 'N/A')).classes('bg-blue-100 p-2 rounded')
                    
                    # Antwoord
                    ui.label('Antwoord').classes('text-lg font-bold mt-2')
                    with ui.scroll_area().classes('h-64'):
                        ui.markdown(doc.content)
                    
                    # Acties
                    ui.separator()
                    
                    with ui.row().classes('w-full mt-2'):
                        async def delete_document(doc_id=doc_id):
                            if doc_id in project["shortlist"]:
                                del project["shortlist"][doc_id]
                            ui.notify(f'Document {meta.get("km_number", "N/A")} verwijderd')
                            await ui.run_javascript('location.reload()')
                        
                        async def save_document(doc_id=doc_id):
                            for did in project["shortlist"]:
                                project["shortlist"][did]['saved_for_next_step'] = (did == doc_id)
                            ui.notify(f'Document {meta.get("km_number", "N/A")} opgeslagen')
                            await ui.run_javascript('location.reload()')
                        
                        async def copy_document(doc_id=doc_id):
                            ui.notify(f'Antwoord gekopieerd voor document {meta.get("km_number", "N/A")}')
                        
                        ui.button('🗑️ Verwijder dit document', on_click=delete_document).classes('mr-2')
                        ui.button('💾 Bewaar alleen dit document', on_click=save_document).classes('mr-2')
                        ui.button('📋 Kopieer antwoord', on_click=copy_document)