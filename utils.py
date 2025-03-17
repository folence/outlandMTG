#!/usr/bin/env python3
"""
Utility functions for the OutlandMTG application.
Includes path handling, logging setup, data management, and other shared functionality.
This module serves as a central location for common functions used across the application.
"""

import os
import sys
import platform
import logging
import json
import pickle
import re
import hashlib
import time
import random
import functools
from typing import Dict, Any, List, Optional, Union, Tuple, Set, Callable
from pathlib import Path
import datetime
from datetime import datetime, timedelta

#==============================================================================
# PLATFORM AND ENVIRONMENT DETECTION
#==============================================================================

SYSTEM = platform.system()
IS_WINDOWS = SYSTEM == "Windows"
IS_DOCKER = os.path.exists('/.dockerenv')

# Constants for rate limiting
DEFAULT_MAX_RETRIES = 5
DEFAULT_INITIAL_BACKOFF = 1
DEFAULT_MAX_BACKOFF = 60
DEFAULT_BACKOFF_FACTOR = 2
DEFAULT_JITTER = 0.5  # Random jitter factor to avoid synchronized retries

#==============================================================================
# PATH AND FILE MANAGEMENT
#==============================================================================

def get_data_dir() -> Path:
    """
    Get the appropriate data directory based on platform and environment.
    
    Returns:
        Path: The path to the data directory, which is guaranteed to exist
    """
    if IS_DOCKER:
        # In Docker, use the mounted volume
        path = Path('/app/data')
    else:
        # Get the directory of the current script
        base_dir = Path(os.path.dirname(os.path.abspath(__file__)))
        path = base_dir / 'data'
        
    # Ensure the directory exists
    os.makedirs(path, exist_ok=True)
    return path

def ensure_dir_exists(path: Path) -> Path:
    """
    Ensure a directory exists and return the path.
    
    Args:
        path: The directory path to ensure exists
        
    Returns:
        Path: The same path that was passed in
    """
    os.makedirs(path, exist_ok=True)
    return path

def get_log_dir() -> Path:
    """
    Get the log directory.
    
    Returns:
        Path: The path to the log directory, which is guaranteed to exist
    """
    log_dir = get_data_dir() / 'logs'
    return ensure_dir_exists(log_dir)

def get_log_file(name: str) -> Path:
    """
    Get the path to a log file.
    
    Args:
        name: The name of the log file
        
    Returns:
        Path: The full path to the log file
    """
    return get_log_dir() / name

def get_file_age_days(filename: str) -> float:
    """
    Get the age of a file in days.
    
    Args:
        filename: The name of the file in the data directory
        
    Returns:
        float: The age of the file in days, or infinity if the file doesn't exist
    """
    file_path = get_data_dir() / filename
    if not os.path.exists(file_path):
        return float('inf')
    
    file_time = os.path.getmtime(file_path)
    current_time = datetime.now().timestamp()
    return (current_time - file_time) / (24 * 60 * 60)

def get_file_size(file_path: Union[str, Path]) -> int:
    """
    Get the size of a file in bytes.
    
    Args:
        file_path: The path to the file
        
    Returns:
        int: The size of the file in bytes, or 0 if the file doesn't exist
    """
    try:
        return os.path.getsize(file_path)
    except:
        return 0

#==============================================================================
# JSON DATA HANDLING
#==============================================================================

def load_json_file(filename: str) -> Dict[str, Any]:
    """
    Load a JSON file from the data directory.
    
    Args:
        filename: The name of the file in the data directory
        
    Returns:
        Dict: The parsed JSON data, or an empty dict if the file doesn't exist
    """
    file_path = get_data_dir() / filename
    try:
        if os.path.exists(file_path):
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {}
    except Exception as e:
        logging.error(f"Error loading JSON file {filename}: {str(e)}")
        return {}

def save_json_file(data: Dict[str, Any], filename: str) -> bool:
    """
    Save data to a JSON file in the data directory.
    
    Args:
        data: The data to save
        filename: The name of the file in the data directory
        
    Returns:
        bool: True if the save was successful, False otherwise
    """
    file_path = get_data_dir() / filename
    try:
        # Ensure data directory exists
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        logging.error(f"Error saving JSON file {filename}: {str(e)}")
        return False

def save_json_with_metadata(data: List[Dict[str, Any]], filename: str) -> bool:
    """
    Save data to a JSON file with metadata (last_updated, card_count, etc.).
    
    Args:
        data: The data to save
        filename: The name of the file in the data directory
        
    Returns:
        bool: True if the save was successful, False otherwise
    """
    metadata = {
        "last_updated": datetime.now().isoformat(),
        "card_count": len(data),
        "data_hash": hashlib.md5(json.dumps(data, sort_keys=True).encode()).hexdigest()
    }
    
    output = {
        "metadata": metadata,
        "cards": data
    }
    
    return save_json_file(output, filename)

def load_pickle_file(filename: str) -> Any:
    """
    Load a pickle file from the data directory.
    
    Args:
        filename: The name of the file in the data directory
        
    Returns:
        Any: The unpickled data, or None if the file doesn't exist
    """
    file_path = get_data_dir() / filename
    try:
        if os.path.exists(file_path):
            with open(file_path, 'rb') as f:
                return pickle.load(f)
        return None
    except Exception as e:
        logging.error(f"Error loading pickle file {filename}: {str(e)}")
        return None

def save_pickle_file(data: Any, filename: str) -> bool:
    """
    Save data to a pickle file in the data directory.
    
    Args:
        data: The data to save
        filename: The name of the file in the data directory
        
    Returns:
        bool: True if the save was successful, False otherwise
    """
    file_path = get_data_dir() / filename
    try:
        # Ensure data directory exists
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        
        with open(file_path, 'wb') as f:
            pickle.dump(data, f)
        return True
    except Exception as e:
        logging.error(f"Error saving pickle file {filename}: {str(e)}")
        return False

#==============================================================================
# DATE AND TIME UTILITIES
#==============================================================================

def format_timestamp(timestamp: Optional[float] = None) -> str:
    """
    Format a timestamp as a human-readable string.
    
    Args:
        timestamp: The timestamp to format, or None for current time
        
    Returns:
        str: The formatted timestamp as YYYY-MM-DD HH:MM:SS
    """
    if timestamp is None:
        dt = datetime.now()
    else:
        dt = datetime.fromtimestamp(timestamp)
    return dt.strftime("%Y-%m-%d %H:%M:%S")

def get_next_sunday_1am() -> datetime:
    """
    Get the next Sunday at 1:00 AM.
    
    Returns:
        datetime: The datetime of next Sunday at 1:00 AM
    """
    now = datetime.now()
    days_until_sunday = (6 - now.weekday()) % 7  # 6 is Sunday
    if days_until_sunday == 0 and now.hour >= 1:
        days_until_sunday = 7
    next_sunday = now + timedelta(days=days_until_sunday)
    return datetime(next_sunday.year, next_sunday.month, next_sunday.day, 1, 0, 0)

#==============================================================================
# CARD NAME NORMALIZATION AND TEXT PROCESSING
#==============================================================================

def normalize_card_name(name: str) -> str:
    """
    Normalize a card name for comparison.
    
    Args:
        name: The card name to normalize
        
    Returns:
        str: The normalized card name
    """
    return name.lower().strip().replace(',', '').replace('\'', '').replace(' ', '')

def clean_card_name(name: str) -> str:
    """
    Clean up card name by removing suffixes and extra spaces.
    
    Args:
        name: The card name to clean
        
    Returns:
        str: The cleaned card name
    """
    name = name.strip()
    patterns = [
        r'\s*\(Enkeltkort\)\s*',
        r'\s*\([^)]*Edition\)\s*',
        r'\s*\([^)]*Set\)\s*',
        r'\s*\([^)]*\)\s*',  # Remove any remaining parentheses
        r'\s+',  # Replace multiple spaces with single space
    ]
    for pattern in patterns:
        name = re.sub(pattern, ' ', name)
    return name.strip()

def extract_price(price_text: str) -> float:
    """
    Extract price from price text, handling different formats.
    
    Args:
        price_text: The price text to extract from
        
    Returns:
        float: The extracted price
    """
    try:
        # Remove all non-digit characters except comma and period
        price_clean = re.sub(r'[^\d,.]', '', price_text)
        # Replace comma with period for decimal
        price_clean = price_clean.replace(',', '.')
        # Convert to float
        return float(price_clean)
    except Exception as e:
        logging.error(f"Error parsing price '{price_text}': {str(e)}")
        return 0.0

#==============================================================================
# HTTP AND NETWORKING
#==============================================================================

def safe_request(func: Callable) -> Callable:
    """
    Decorator for safely making requests with exponential backoff.
    
    Args:
        func: The function to decorate
        
    Returns:
        Callable: The decorated function
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        max_retries = kwargs.pop('max_retries', DEFAULT_MAX_RETRIES)
        base_delay = kwargs.pop('base_delay', DEFAULT_INITIAL_BACKOFF)
        
        for attempt in range(max_retries):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                if attempt == max_retries - 1:
                    raise
                
                delay = base_delay * (DEFAULT_BACKOFF_FACTOR ** attempt) + random.uniform(0, DEFAULT_JITTER)
                logging.warning(f"Request failed: {str(e)}. Retrying in {delay:.2f} seconds...")
                time.sleep(delay)
    
    return wrapper

#==============================================================================
# CURRENCY AND PRICE UTILITIES
#==============================================================================

def nok_to_usd(nok_price: float) -> float:
    """
    Convert NOK to USD at a fixed exchange rate.
    
    Args:
        nok_price: The price in NOK
        
    Returns:
        float: The equivalent price in USD
    """
    return nok_price * 0.09  # Fixed exchange rate

def eur_to_usd(eur_price: float) -> float:
    """
    Convert EUR to USD at a fixed exchange rate.
    
    Args:
        eur_price: The price in EUR
        
    Returns:
        float: The equivalent price in USD
    """
    return eur_price * 1.05  # Fixed exchange rate 