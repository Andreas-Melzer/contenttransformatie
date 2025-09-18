import unittest
from config import get_logger, set_log_level
import logging


class TestLogger(unittest.TestCase):
    """Test cases for the logger singleton implementation."""

    def test_logger_singleton(self):
        """Test that the logger is a singleton."""
        logger1 = get_logger()
        logger2 = get_logger()
        
        # Both should be the same instance
        self.assertIs(logger1, logger2)

    def test_logger_functionality(self):
        """Test that the logger can log messages."""
        logger = get_logger()
        
        # Test that logger has the expected name
        self.assertEqual(logger.name, "contentcreatie")
        
        # Test that we can set log level
        original_level = logger.level
        set_log_level(logging.DEBUG)
        self.assertEqual(logger.level, logging.DEBUG)
        set_log_level(original_level)  # Reset to original

    def test_logger_import(self):
        """Test that we can import the logger components."""
        # This test just verifies imports work
        from config.logger import LoggerSingleton
        from config import get_logger, set_log_level
        
        # Verify we can create an instance
        logger_instance = LoggerSingleton()
        self.assertIsNotNone(logger_instance)
        
        # Verify we can get the logger
        logger = get_logger()
        self.assertIsNotNone(logger)


if __name__ == "__main__":
    unittest.main()