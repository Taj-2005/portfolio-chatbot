"""
Logging configuration for the Portfolio Chatbot.

Provides structured logging with configurable levels and formatting.
"""

import logging
import sys
from typing import Optional
from ..config import settings


def setup_logger(
    name: str,
    level: Optional[str] = None,
    log_file: Optional[str] = None
) -> logging.Logger:
    """
    Set up a logger with the specified name and level.
    
    Args:
        name: Logger name (typically __name__ of the calling module).
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL).
               If None, uses settings.LOG_LEVEL.
        log_file: Optional file path to write logs to.
    
    Returns:
        logging.Logger: Configured logger instance.
    """
    logger = logging.getLogger(name)
    
    # Set level
    log_level = level or settings.LOG_LEVEL
    logger.setLevel(getattr(logging, log_level.upper()))
    
    # Avoid adding handlers multiple times
    if logger.handlers:
        return logger
    
    # Create formatter
    formatter = logging.Formatter(settings.LOG_FORMAT)
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # File handler (optional)
    if log_file:
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    
    return logger


# Default application logger
app_logger = setup_logger('portfolio_chatbot')
