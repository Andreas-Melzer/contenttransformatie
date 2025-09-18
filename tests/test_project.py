"""
Unit tests for the Project class.
"""

import pytest
import os
import json
import tempfile
from unittest.mock import patch, mock_open
from interface.project import Project

class TestProject:
    """Test cases for the Project class."""
    
    def test_project_initialization(self):
        """Test Project initialization with required parameters."""
        vraag = "Test vraag"
        subvragen = ["Subvraag 1", "Subvraag 2"]
        
        project = Project(vraag=vraag, subvragen=subvragen)
        
        assert project.vraag == vraag
        assert project.subvragen == subvragen
        assert project.id is not None
        assert isinstance(project.id, str)
        
    def test_project_initialization_with_id(self):
        """Test Project initialization with a specific ID."""
        project_id = "test-project-id"
        vraag = "Test vraag"
        subvragen = ["Subvraag 1", "Subvraag 2"]
        
        project = Project(vraag=vraag, subvragen=subvragen, project_id=project_id)
        
        assert project.id == project_id
        assert project.vraag == vraag
        assert project.subvragen == subvragen
        
    def test_project_property_getters(self):
        """Test Project property getters."""
        project_id = "test-project-id"
        vraag = "Test vraag"
        subvragen = ["Subvraag 1", "Subvraag 2"]
        
        project = Project(vraag=vraag, subvragen=subvragen, project_id=project_id)
        
        # Test all property getters
        assert project.id == project_id
        assert project.vraag == vraag
        assert project.subvragen == subvragen
        assert project.messages == [{"role": "assistant", "content": f"Oké, ik start het onderzoek voor de vraag: '{vraag}' en subvragen {subvragen}. Laten we beginnen."}]
        assert project.agent_found_documents == {}
        assert project.self_found_documents == {}
        assert project.scratchpad == []
        assert project.saved_selection_consolidate == []
        assert project.selected_doc_id is None
        assert project.consolidate_messages == []
        assert project.rewrite_messages == []
        assert project.consolidated_text == ""
        assert project.consolidated_json == {}
        assert project.rewritten_text == {}
        
    def test_project_property_setters(self):
        """Test Project property setters."""
        project = Project(vraag="Test vraag", subvragen=[])
        
        # Test vraag setter
        new_vraag = "Nieuwe test vraag"
        project.vraag = new_vraag
        assert project.vraag == new_vraag
        
        # Test subvragen setter
        new_subvragen = ["Nieuwe subvraag 1", "Nieuwe subvraag 2"]
        project.subvragen = new_subvragen
        assert project.subvragen == new_subvragen
        
    @patch('interface.project.os.path.exists')
    @patch('interface.project.os.makedirs')
    @patch('interface.project.open', new_callable=mock_open)
    def test_project_save(self, mock_file, mock_makedirs, mock_exists):
        """Test Project save method."""
        mock_exists.return_value = False
        
        project = Project(vraag="Test vraag", subvragen=["Subvraag 1"])
        
        with patch.object(project, '_get_path') as mock_get_path:
            mock_get_path.return_value = "/fake/path/test-project-id.json"
            
            project.save()
            
            # Check that makedirs was called
            mock_makedirs.assert_called_once()
            
            # Check that open was called for each file type
            assert mock_file.call_count == 4  # metadata, search, consolidate, rewrite
            
    def test_project_to_metadata_dict(self):
        """Test Project to_metadata_dict method."""
        project_id = "test-project-id"
        vraag = "Test vraag"
        subvragen = ["Subvraag 1", "Subvraag 2"]
        
        project = Project(vraag=vraag, subvragen=subvragen, project_id=project_id)
        
        metadata = project.to_metadata_dict()
        
        assert metadata["id"] == project_id
        assert metadata["vraag"] == vraag
        assert metadata["subvragen"] == subvragen
        
    def test_project_to_search_data_dict(self):
        """Test Project to_search_data_dict method."""
        project = Project(vraag="Test vraag", subvragen=["Subvraag 1"])
        
        search_data = project.to_search_data_dict()
        
        assert "messages" in search_data
        assert "agent_found_documents" in search_data
        assert "self_found_documents" in search_data
        assert "scratchpad" in search_data
        assert "selected_doc_id" in search_data
        
    def test_project_to_consolidate_data_dict(self):
        """Test Project to_consolidate_data_dict method."""
        project = Project(vraag="Test vraag", subvragen=["Subvraag 1"])
        
        consolidate_data = project.to_consolidate_data_dict()
        
        assert "consolidate_messages" in consolidate_data
        assert "consolidated_json" in consolidate_data
        assert "saved_selection_consolidate" in consolidate_data
        assert "consolidated_text" in consolidate_data
        
    def test_project_to_rewrite_data_dict(self):
        """Test Project to_rewrite_data_dict method."""
        project = Project(vraag="Test vraag", subvragen=["Subvraag 1"])
        
        rewrite_data = project.to_rewrite_data_dict()
        
        assert "rewrite_messages" in rewrite_data
        assert "rewritten_text" in rewrite_data
        
    def test_project_found_documents_property(self):
        """Test Project found_documents property."""
        project = Project(vraag="Test vraag", subvragen=[])
        
        # Add some documents to both agent and self found
        project.agent_found_documents = {"doc1": 0.8, "doc2": 0.6}
        project.self_found_documents = {"doc3": 0.9, "doc4": 0.7}
        
        found_docs = project.found_documents
        
        assert len(found_docs) == 4
        assert "doc1" in found_docs
        assert "doc2" in found_docs
        assert "doc3" in found_docs
        assert "doc4" in found_docs
        
    def test_project_upsert_document(self):
        """Test Project upsert_document method."""
        project = Project(vraag="Test vraag", subvragen=[])
        
        # Add a document
        project.upsert_document("doc1", 0.8)
        
        assert "doc1" in project.agent_found_documents
        assert project.agent_found_documents["doc1"] == 0.8
        
        # Update the document
        project.upsert_document("doc1", 0.9)
        
        assert project.agent_found_documents["doc1"] == 0.9