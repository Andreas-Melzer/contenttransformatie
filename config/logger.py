import logging
import sys
from pathlib import Path
from typing import Optional

from config.settings import settings


class LoggerSingleton:
    """
    A singleton logger implementation that ensures only one instance of the logger
    is created and used throughout the application.
    """
    _instance: Optional['LoggerSingleton'] = None
    _logger: Optional[logging.Logger] = None

    def __new__(cls) -> 'LoggerSingleton':
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialize_logger()
        return cls._instance

    def _initialize_logger(self) -> None:
        """Initialize the logger with appropriate configuration."""
        # Create logger
        self._logger = logging.getLogger("contentcreatie")
        self._logger.setLevel(logging.DEBUG)

        # Prevent adding handlers multiple times
        if not self._logger.handlers:
            # Create formatter
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )

            # Create console handler
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setLevel(logging.INFO)
            console_handler.setFormatter(formatter)
            self._logger.addHandler(console_handler)

            # Create file handler if log directory exists or can be created
            try:
                log_dir = settings.data_root / "logs"
                log_dir.mkdir(exist_ok=True)
                file_handler = logging.FileHandler(log_dir / "app.log")
                file_handler.setLevel(logging.DEBUG)
                file_handler.setFormatter(formatter)
                self._logger.addHandler(file_handler)
            except Exception as e:
                # If file logging fails, continue with console logging only
                self._logger.warning(f"File logging setup failed: {e}")

    def get_logger(self) -> logging.Logger:
        """Return the configured logger instance."""
        if self._logger is None:
            self._initialize_logger()
        return self._logger

    def set_level(self, level: int) -> None:
        """Set the logging level for all handlers."""
        if self._logger:
            self._logger.setLevel(level)
            for handler in self._logger.handlers:
                handler.setLevel(level)


# Create a global instance
_logger_singleton = LoggerSingleton()


def get_logger() -> logging.Logger:
    """
    Get the singleton logger instance.
    
    Returns:
        logging.Logger: The configured logger instance.
    """
    return _logger_singleton.get_logger()


def set_log_level(level: int) -> None:
    """
    Set the logging level for the application logger.
    
    Args:
        level (int): The logging level to set (e.g., logging.DEBUG, logging.INFO)
    """
    _logger_singleton.set_level(level)