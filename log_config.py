#!/usr/bin/env python3
"""
Centralized logging configuration for OutlandMTG.
"""

import os
import logging
from logging.handlers import RotatingFileHandler
from typing import Optional
import sys
import utils

# Default logging levels
DEFAULT_LOG_LEVEL = logging.INFO
DEFAULT_CONSOLE_LEVEL = logging.WARNING

# Configure root logger to catch any unconfigured loggers
def configure_root_logger() -> None:
    """Configure the root logger with basic settings."""
    root_logger = logging.getLogger()
    
    if not root_logger.handlers:
        # Set root logger level to DEBUG to allow all messages to pass through
        root_logger.setLevel(logging.DEBUG)
        
        # Add console handler with WARNING level by default
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(DEFAULT_CONSOLE_LEVEL)
        formatter = logging.Formatter('%(levelname)s: %(message)s')
        console_handler.setFormatter(formatter)
        root_logger.addHandler(console_handler)

def get_logger(name: str, log_file: str, 
               file_level: int = DEFAULT_LOG_LEVEL,
               console_level: int = DEFAULT_CONSOLE_LEVEL) -> logging.Logger:
    """
    Get a logger with the specified name and configuration.
    
    Args:
        name: The name of the logger
        log_file: The name of the log file
        file_level: The logging level for the file handler
        console_level: The logging level for the console handler
        
    Returns:
        A configured logger
    """
    logger = logging.getLogger(name)
    
    # Only configure if not already configured
    if not logger.handlers:
        # Set logger level to DEBUG to allow all messages to pass through
        logger.setLevel(logging.DEBUG)
        
        # Create log directory if it doesn't exist
        log_dir = utils.get_log_dir()
        
        # Configure file handler with rotation
        log_path = log_dir / log_file
        file_handler = RotatingFileHandler(
            log_path, 
            maxBytes=10*1024*1024,  # 10MB
            backupCount=5
        )
        # Always set file handler to DEBUG for tests
        if name == "test_app":
            file_handler.setLevel(logging.DEBUG)
        else:
            file_handler.setLevel(file_level)
            
        file_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)
        
        # Add console handler unless console output is disabled
        if console_level is not None:
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setLevel(console_level)
            console_formatter = logging.Formatter('%(levelname)s: %(message)s')
            console_handler.setFormatter(console_formatter)
            logger.addHandler(console_handler)
            
    return logger

def test_logging_config() -> bool:
    """
    Test logging configuration by writing test log entries.
    
    Returns:
        True if logging is configured correctly, False otherwise
    """
    try:
        # Get a test logger
        test_logger = get_logger("test_config", "test_config.log")
        
        # Write test messages to the log
        test_logger.debug("Test debug message")
        test_logger.info("Test info message")
        test_logger.warning("Test warning message")
        test_logger.error("Test error message")
        
        # Check if log file was created
        log_file_path = utils.get_log_dir() / "test_config.log"
        return os.path.exists(log_file_path)
    except Exception as e:
        print(f"Logging configuration test failed: {str(e)}")
        return False 