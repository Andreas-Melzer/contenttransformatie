"""
Configuration file for pytest.
Contains fixtures and setup/teardown functions for tests.
"""

import pytest
import os
import sys
import tempfile
import shutil
from unittest.mock import Mock, patch

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

@pytest.fixture
def temp_dir():
    """Create a temporary directory for tests."""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    shutil.rmtree(temp_dir)

@pytest.fixture
def mock_project():
    """Create a mock project object for testing."""
    from interface.project import Project
    project = Mock(spec=Project)
    project.id = "test-project-id"
    project.vraag = "Test vraag"
    project.subvragen = ["Test subvraag 1", "Test subvraag 2"]
    project.messages = []
    project.agent_found_documents = {}
    project.self_found_documents = {}
    project.scratchpad = []
    project.saved_selection_consolidate = []
    project.selected_doc_id = None
    project.consolidate_messages = []
    project.rewrite_messages = []
    project.consolidated_text = ""
    project.consolidated_json = {}
    project.rewritten_text = {}
    return project