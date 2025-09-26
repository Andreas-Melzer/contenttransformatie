"""
Unit tests for the JSON saving tools.
"""

import pytest
import json
from unittest.mock import MagicMock
from interface.implementations.tools.save_rewritten_json_tool import SaveRewrittenJsonTool
from interface.implementations.tools.save_consolidated_json_tool import SaveConsolidatedJsonTool
from interface.project import Project

class TestTools:
    """Test cases for the JSON saving tools."""

    def test_successful_execution(self):
        """Test successful execution with valid JSON content."""
        # Create a mock project
        project = MagicMock(spec=Project)
        project.id = "test-project-id"

        # Create the tool
        tool = SaveRewrittenJsonTool(project=project)

        # Valid JSON content
        valid_json = json.dumps({"content": "This is rewritten content"})

        # Execute the tool
        result = tool.execute(content=valid_json)

        # Verify the result
        assert "updated and saved successfully" in result
        # The mock doesn't actually update, so we just verify the success message

    def test_invalid_json_content(self):
        """Test failure with invalid JSON content."""
        # Create a mock project
        project = MagicMock(spec=Project)
        project.id = "test-project-id"

        # Create the tool
        tool = SaveRewrittenJsonTool(project=project)

        # Invalid JSON content
        invalid_json = "This is not valid JSON"

        # Execute the tool
        result = tool.execute(content=invalid_json)

        # Verify the result
    def test_save_consolidated_json_success(self):
        """Test successful execution of SaveConsolidatedJsonTool with valid parameters."""
        # Create a mock project
        project = MagicMock(spec=Project)
        project.id = "test-project-id"

        # Create the tool
        tool = SaveConsolidatedJsonTool(project=project)

        # Valid parameters
        valid_params = {
            "hoofdvraag": "Main question",
            "consolidatie": [
                {
                    "vraag": "Question 1",
                    "publieke_informatie": {"fragmenten": [{"tekst_fragment": "Fragment 1", "bron_km": ["Source 1"]}]},
                    "interne_informatie": {"fragmenten": [{"tekst_fragment": "Fragment 2", "bron_km": ["Source 2"]}]}
                }
            ],
            "subvragen_consolidatie": [
                {
                    "vraag": "Sub-question 1",
                    "publieke_informatie": {"fragmenten": [{"tekst_fragment": "Fragment 3", "bron_km": ["Source 3"]}]},
                    "interne_informatie": {"fragmenten": [{"tekst_fragment": "Fragment 4", "bron_km": ["Source 4"]}]}
                }
            ],
            "gedetecteerde_conflicten": [
                {
                    "conflict_beschrijving": "Conflict 1",
                    "bron_km": ["Source 1", "Source 2"]
                }
            ],
            "informatie_hiaten": [
                {
                    "hiaat_beschrijving": "Gap 1",
                    "relevante_vraag": "Question 1"
                }
            ]
        }

        # Execute the tool
        result = tool.execute(**valid_params)

        # Verify the result
        assert "updated and saved successfully" in result

    def test_save_consolidated_json_missing_required(self):
        """Test failure of SaveConsolidatedJsonTool with missing required parameters."""
        # Create a mock project
        project = MagicMock(spec=Project)
        project.id = "test-project-id"

        # Create the tool
        tool = SaveConsolidatedJsonTool(project=project)

        # Missing required parameters
        invalid_params = {
            "hoofdvraag": "Main question",
            # Missing consolidatie, subvragen_consolidatie, etc.
        }

        # Execute the tool
        result = tool.execute(**invalid_params)

        # Verify the result
        assert "Error: Invalid input for tool save_consolidated_json:" in result

    def test_save_consolidated_json_invalid_types(self):
        """Test failure of SaveConsolidatedJsonTool with invalid parameter types."""
        # Create a mock project
        project = MagicMock(spec=Project)
        project.id = "test-project-id"

        # Create the tool
        tool = SaveConsolidatedJsonTool(project=project)

        # Invalid parameter types
        invalid_params = {
            "hoofdvraag": 123,  # Should be a string
            "consolidatie": "not a list",  # Should be a list
            "subvragen_consolidatie": "not a list",  # Should be a list
            "gedetecteerde_conflicten": "not a list",  # Should be a list
            "informatie_hiaten": "not a list",  # Should be a list
        }

        # Execute the tool
        result = tool.execute(**invalid_params)

        # Verify the result
        assert "Error: Invalid input for tool save_consolidated_json:" in result

    def test_missing_content_parameter(self):
        """Test failure with missing content parameter."""
        # Create a mock project
        project = MagicMock(spec=Project)
        project.id = "test-project-id"

        # Create the tool
        tool = SaveRewrittenJsonTool(project=project)

        # Execute the tool without the content parameter
        result = tool.execute()

        # Verify the result
        assert "Error: Invalid input for tool save_rewritten_json: 'content' is a required property" in result