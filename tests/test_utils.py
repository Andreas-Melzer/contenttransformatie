"""
Unit tests for utility functions.
"""

import pytest
import os
import sys

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

def test_content_extraction_utils_import():
    """Test that content_extraction_utils can be imported."""
    try:
        import utils.content_extraction_utils
        assert True
    except ImportError:
        assert False, "content_extraction_utils could not be imported"
        
def test_scrub_json_import():
    """Test that scrub_json can be imported."""
    try:
        import utils.scrub_json
        assert True
    except ImportError:
        assert False, "scrub_json could not be imported"