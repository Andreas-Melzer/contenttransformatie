from nicegui import ui

def apply_custom_css():
    """Applies custom CSS to the NiceGUI application."""
    ui.add_head_html('''
    <style>
        /* Main layout and theme */
        body {
            background-color: #F0F2F6;
            color: #0E1117;
        }
        
        /* Document Viewer Styling */
        .document-viewer {
            padding: 2rem;
            background-color: white;
            border: 1px solid #E0E0E0;
            border-radius: 10px;
            margin-top: 1rem;
            box-shadow: 0 4px 8px rgba(0,0,0,0.1);
            line-height: 1.6;
        }
        
        .document-viewer h2 {
            color: #0070C0;
            border-bottom: 2px solid #0070C0;
            padding-bottom: 0.5rem;
        }
        
        .metadata-chip {
            display: inline-block;
            background-color: #E0E0E0;
            color: #333;
            padding: 5px 12px;
            border-radius: 15px;
            margin: 5px 5px 5px 0;
            font-size: 0.9em;
        }
        
        /* Table styling */
        .table-container {
            border: 1px solid #C0C0C0;
            border-radius: 5px;
            overflow: hidden;
        }
        
        .table-header {
            font-weight: bold;
            padding: 0.75rem;
            background-color: #0070C0;
            color: white;
            text-align: left;
        }
        
        .table-row {
            border-bottom: 1px solid #D1D1D1;
            transition: background-color 0.2s ease;
        }
        
        .table-row:nth-child(even) {
            background-color: #F8F9FA;
        }
        
        .table-row:hover {
            background-color: #E9ECEF;
        }
        
        /* Card styling */
        .project-card {
            border: 1px solid #D1D1D1;
            border-radius: 8px;
            padding: 1rem;
            margin-bottom: 1rem;
            background-color: white;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        
        /* Button styling */
        .primary-button {
            background-color: #0070C0;
            color: white;
            border: none;
            padding: 0.5rem 1rem;
            border-radius: 4px;
            cursor: pointer;
        }
        
        .primary-button:hover {
            background-color: #005A9E;
        }
        
        .secondary-button {
            background-color: #F0F2F6;
            color: #0E1117;
            border: 1px solid #D1D1D1;
            padding: 0.5rem 1rem;
            border-radius: 4px;
            cursor: pointer;
        }
        
        .secondary-button:hover {
            background-color: #E0E0E0;
        }
    </style>
    ''')