"""
Logger utility for DinoAir
Provides centralized logging functionality
"""

from datetime import datetime
import logging
from pathlib import Path
import sys
from typing import Any, Optional


class Logger:
    """Centralized logging utility"""

    _instance: Optional["Logger"] = None
    _initialized: bool = False

    def __new__(cls) -> "Logger":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if not self._initialized:
            self.setup_logging()
            Logger._initialized = True

    def setup_logging(self) -> None:
        """Setup logging configuration.

        Note:
            If structured logging is already configured via
            utils.structured_logging.setup_logging(), this method will not
            reconfigure handlers. It will simply obtain the namespaced logger.
        """
        root = logging.getLogger()
        if getattr(root, "_dinoair_structured_logging_configured", False):
            # Structured logging already set up; just obtain a namespaced logger
            self.logger = logging.getLogger("DinoAir")
            return

        # Fallback basic configuration (legacy)
        log_dir = Path(__file__).parent.parent.parent / "logs"
        log_dir.mkdir(exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d")
        log_file = log_dir / f"dinoair_{timestamp}.log"

        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            handlers=[
                logging.FileHandler(log_file, encoding="utf-8"),
                logging.StreamHandler(sys.stdout),
            ],
        )

        self.logger = logging.getLogger("DinoAir")

    def info(self, message: str, *args: Any, **kwargs: Any) -> None:
        """Log info message"""
        self.logger.info(message, *args, **kwargs)

    def warning(self, message: str, *args: Any, **kwargs: Any) -> None:
        """Log warning message"""
        self.logger.warning(message, *args, **kwargs)

    def error(self, message: str, *args: Any, **kwargs: Any) -> None:
        """Log error message"""
        self.logger.error(message, *args, **kwargs)

    def debug(self, message: str, *args: Any, **kwargs: Any) -> None:
        """Log debug message"""
        self.logger.debug(message, *args, **kwargs)

    def critical(self, message: str, *args: Any, **kwargs: Any) -> None:
        """Log critical message"""
        self.logger.critical(message, *args, **kwargs)


# Convenience functions for direct import
def log_info(message: str) -> None:
    """Convenience wrapper for info logging."""
    Logger().info(message)


def log_warning(message: str) -> None:
    """Convenience wrapper for warning logging."""
    Logger().warning(message)


def log_error(message: str) -> None:
    """Convenience wrapper for error logging."""
    Logger().error(message)


def log_debug(message: str) -> None:
    """Convenience wrapper for debug logging."""
    Logger().debug(message)


def log_critical(message: str) -> None:
    """Convenience wrapper for critical logging."""
    Logger().critical(message)
