import streamlit as st

def apply_custom_css():
    """Applies custom CSS to the Streamlit application."""
    custom_css = """
    <style>
        /* Main layout and theme */
        [data-testid="stAppViewContainer"] > .main { background-color: #F0F2F6; }
        .stApp, .stMarkdown p { color: #0E1117; }
        [data-testid="stSidebar"] { background-color: #FFFFFF; padding: 1rem; }
        
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
        .document-viewer .metadata-chip {
            display: inline-block;
            background-color: #E0E0E0;
            color: #333;
            padding: 5px 12px;
            border-radius: 15px;
            margin: 5px 5px 5px 0;
            font-size: 0.9em;
        }

        /* --- FINAL CSS FOR EXCEL-LIKE TABLE VIEW --- */
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
        .compact-table > div[data-testid="stVerticalBlock"] {
            border-bottom: 1px solid #D1D1D1;
            transition: background-color 0.2s ease;
        }
        .compact-table > div[data-testid="stVerticalBlock"]:last-child {
            border-bottom: none;
        }
        .compact-table > div[data-testid="stVerticalBlock"]:nth-child(even) {
            background-color: #F8F9FA;
        }
        .compact-table > div[data-testid="stVerticalBlock"]:hover {
            background-color: #E9ECEF;
        }
        .compact-table div[data-testid="stHorizontalBlock"] > div {
            border-right: 1px solid #D1D1D1;
        }
        .compact-table div[data-testid="stHorizontalBlock"] > div:last-child {
            border-right: none;
        }
        .compact-table .stMarkdown, .compact-table .stButton {
            padding: 0.5rem 0.75rem;
            min-height: 55px;
            display: flex;
            align-items: center;
        }
        .compact-table .stButton button {
            width: 100%;
        }
    </style>
    """
    st.markdown(custom_css, unsafe_allow_html=True)