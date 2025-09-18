"""
Example script demonstrating how to use the logger singleton in the config module.
"""

import sys
import os
import logging

# Add the parent directory to the Python path so we can import config
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from config import get_logger, set_log_level


def main():
    # Get the logger instance
    logger = get_logger()
    
    # Log some messages at different levels
    logger.debug("This is a debug message")
    logger.info("This is an info message")
    logger.warning("This is a warning message")
    logger.error("This is an error message")
    
    # Change the log level
    set_log_level(logging.DEBUG)
    logger.debug("This debug message will now be visible")
    
    # Demonstrate that it's a singleton
    logger1 = get_logger()
    logger2 = get_logger()
    
    if logger1 is logger2:
        logger.info("Both logger instances are the same (singleton works correctly)")
    else:
        logger.error("Singleton pattern is not working correctly")


if __name__ == "__main__":
    main()