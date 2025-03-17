#!/usr/bin/env python3
"""
Test suite for Outland MTG Finder
"""

import pytest
import json
import os
import tempfile
from pathlib import Path
from app import app, find_edhrec_url, validate_url
import log_config
import utils
import datetime

# Configure test logger
logger = log_config.get_logger(__name__, 'test.log')

@pytest.fixture
def client():
    """Create a test client for the Flask app"""
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client

@pytest.fixture
def reset_rate_limits():
    """Reset rate limiting between tests"""
    # Import here to avoid circular imports
    import app
    # Reset the request history
    app.request_history = {}
    yield

# App tests
def test_home_page(client):
    """Test that the home page loads"""
    response = client.get('/')
    assert response.status_code == 200
    assert b'Outland MTG' in response.data

def test_health_check(client):
    """Test the health check endpoint"""
    response = client.get('/health')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert 'status' in data
    assert data['status'] == 'ok'
    assert 'logs_configured' in data
    assert data['logs_configured'] is True

def test_database_status(client):
    """Test the database status endpoint"""
    response = client.get('/database_status')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert 'outland_database' in data
    assert 'scryfall_database' in data
    assert 'next_scheduled_update' in data
    assert 'auto_update_enabled' in data

def test_validate_url():
    """Test URL validation for EDHRec links"""
    valid_urls = [
        "https://edhrec.com/commanders/kenrith",
        "http://edhrec.com/commanders/kenrith",
        "https://www.edhrec.com/commanders/kenrith"
    ]
    
    invalid_urls = [
        "https://edhrec.com/other/kenrith",
        "https://other-site.com/commanders/kenrith",
        "not-a-url",
        ""
    ]
    
    for url in valid_urls:
        assert validate_url(url) is True
    
    for url in invalid_urls:
        assert validate_url(url) is False

def test_find_edhrec_url():
    """Test EDHRec URL generation"""
    # Test basic URL generation
    url = find_edhrec_url("Kenrith, the Returned King")
    assert url is not None
    assert "edhrec.com/commanders/kenrith" in url.lower()
    
    # Test budget URL generation
    url = find_edhrec_url("Kenrith, the Returned King", max_price=30)
    assert url is not None
    assert "/budget" in url
    
    # Test expensive URL generation
    url = find_edhrec_url("Kenrith, the Returned King", max_price=150)
    assert url is not None
    assert "/expensive" in url

def test_search_commanders(client):
    """Test commander search endpoint"""
    # Test with valid query
    response = client.get('/search_commanders?q=kenrith')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert isinstance(data, list)
    
    # Test with empty query
    response = client.get('/search_commanders?q=')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert isinstance(data, list)
    assert len(data) == 0
    
    # Test with too short query
    response = client.get('/search_commanders?q=a')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert isinstance(data, list)
    assert len(data) == 0

def test_rate_limiting(client, reset_rate_limits):
    """Test rate limiting"""
    # Make multiple requests quickly
    for _ in range(11):  # Should hit rate limit after 10 requests
        client.get('/search_commanders?q=kenrith')
    
    # Next request should be rate limited
    response = client.get('/search_commanders?q=kenrith')
    assert response.status_code == 429
    data = json.loads(response.data)
    assert 'error' in data
    assert 'Rate limit exceeded' in data['error']

def test_error_handling(client, reset_rate_limits):
    """Test error handling"""
    # Test with missing required field - this should work reliably
    response = client.post('/search_commander',
                          json={'max_price': 50},
                          content_type='application/json')
    assert response.status_code == 400
    data = json.loads(response.data)
    assert 'error' in data
    assert 'Commander name is required' in data['error']

def test_logging():
    """Test that logging is working"""
    # Test different log levels
    logger.debug("Test debug message")
    logger.info("Test info message")
    logger.warning("Test warning message")
    logger.error("Test error message")
    
    # Verify log file exists and has content
    log_file = utils.get_log_dir() / 'test.log'
    assert log_file.exists()
    with open(log_file, 'r') as f:
        content = f.read()
        assert "Test debug message" in content
        assert "Test info message" in content
        assert "Test warning message" in content
        assert "Test error message" in content

# Utils tests
class TestUtils:
    """Tests for the utils module"""
    
    def test_get_data_dir(self):
        """Test get_data_dir function"""
        data_dir = utils.get_data_dir()
        assert isinstance(data_dir, Path)
        # Check the path is absolute
        assert data_dir.is_absolute()
        # Path should end with 'data'
        assert data_dir.name == 'data'

    def test_get_log_dir(self):
        """Test get_log_dir function"""
        log_dir = utils.get_log_dir()
        assert isinstance(log_dir, Path)
        # Check the path is absolute
        assert log_dir.is_absolute()
        # Path should end with 'logs'
        assert log_dir.name == 'logs'
        # Path should be a subdirectory of data_dir
        assert log_dir.parent.name == 'data'
        # Directory should exist
        assert log_dir.exists()
        assert log_dir.is_dir()

    def test_get_log_file(self):
        """Test get_log_file function"""
        log_file = utils.get_log_file('test.log')
        assert isinstance(log_file, Path)
        # Path should end with 'test.log'
        assert log_file.name == 'test.log'
        # Parent directory should be logs
        assert log_file.parent.name == 'logs'

    def test_json_file_operations(self):
        """Test JSON file operations"""
        # Create a temporary directory
        with tempfile.TemporaryDirectory() as temp_dir:
            # Mock the get_data_dir function to return our temp directory
            original_get_data_dir = utils.get_data_dir
            utils.get_data_dir = lambda: Path(temp_dir)
            
            try:
                # Test data
                test_data = {'key1': 'value1', 'key2': [1, 2, 3], 'key3': {'nested': 'value'}}
                
                # Test saving
                assert utils.save_json_file(test_data, 'test.json')
                
                # Check the file exists
                json_path = Path(temp_dir) / 'test.json'
                assert json_path.exists()
                
                # Test loading
                loaded_data = utils.load_json_file('test.json')
                assert loaded_data == test_data
                
                # Test loading non-existent file
                empty_data = utils.load_json_file('nonexistent.json')
                assert empty_data == {}
            finally:
                # Restore the original function
                utils.get_data_dir = original_get_data_dir

    def test_normalize_card_name(self):
        """Test normalize_card_name function"""
        # Test various card name formats
        assert utils.normalize_card_name("Lightning Bolt") == "lightningbolt"
        assert utils.normalize_card_name("Jace, the Mind Sculptor") == "jacethemindsculptor"
        assert utils.normalize_card_name("Liliana of the Veil") == "lilianaoftheveil"
        assert utils.normalize_card_name("   Black Lotus   ") == "blacklotus"
        assert utils.normalize_card_name("Gaea's Cradle") == "gaeascradle"
        
        # Test that different variations normalize to the same value
        variations = [
            "Jace, the Mind Sculptor",
            "jace, the mind sculptor",
            "Jace the Mind Sculptor",
            "jace the mind sculptor",
            "JACE, THE MIND SCULPTOR"
        ]
        normalized = utils.normalize_card_name(variations[0])
        for var in variations[1:]:
            assert utils.normalize_card_name(var) == normalized

    def test_format_timestamp(self):
        """Test format_timestamp function"""
        # We'll only test the format pattern instead of exact timestamp 
        # to avoid timezone issues
        
        # Test with current time
        now_formatted = utils.format_timestamp()
        # Verify the format matches YYYY-MM-DD HH:MM:SS
        assert len(now_formatted) == 19
        assert now_formatted[4] == '-' and now_formatted[7] == '-'
        assert now_formatted[10] == ' '
        assert now_formatted[13] == ':' and now_formatted[16] == ':'
        
        # Test with specific timestamp, but don't assert exact time
        timestamp = 1609459200  # 2021-01-01 00:00:00 UTC
        formatted = utils.format_timestamp(timestamp)
        assert formatted.startswith("2021-01-01")  # Only check the date part
        assert len(formatted) == 19
        assert formatted[10] == ' '
        assert formatted[13] == ':' and formatted[16] == ':'

    def test_file_age_days(self):
        """Test get_file_age_days function"""
        # Create a temporary directory
        with tempfile.TemporaryDirectory() as temp_dir:
            # Mock the get_data_dir function to return our temp directory
            original_get_data_dir = utils.get_data_dir
            utils.get_data_dir = lambda: Path(temp_dir)
            
            try:
                # Create a test file
                test_file_path = Path(temp_dir) / 'test_age.txt'
                with open(test_file_path, 'w') as f:
                    f.write('test')
                
                # Test with existing file
                age = utils.get_file_age_days('test_age.txt')
                assert age < 1.0  # File should be less than a day old
                
                # Test with non-existent file
                infinite_age = utils.get_file_age_days('nonexistent.txt')
                assert infinite_age == float('inf')
            finally:
                # Restore the original function
                utils.get_data_dir = original_get_data_dir 