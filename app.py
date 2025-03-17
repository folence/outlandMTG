from flask import Flask, render_template, request, jsonify
import EDH_search
import underpriced_cards
import scryfall_prices
import outlandMTG_database
import asyncio
import json
from datetime import datetime, timedelta
import os
import sys
import time
from functools import wraps
import re
import subprocess
import requests
from bs4 import BeautifulSoup
import log_config
import traceback
import utils
from pathlib import Path

# Configure logging using our centralized config
logger = log_config.get_logger(__name__, 'app.log')
# Configure root logger to catch any unconfigured loggers
log_config.configure_root_logger()

# Create Flask app
app = Flask(__name__)

# Configure Flask's logging to use our system
app.logger = logger

# Add application error handler to log exceptions
@app.errorhandler(Exception)
def handle_exception(e):
    """Log exceptions to the application log"""
    # Get exception information
    error_cls = e.__class__.__name__
    error_msg = str(e)
    
    # Log the error with detailed traceback
    logger.error(f"Unhandled {error_cls}: {error_msg}")
    logger.debug(traceback.format_exc())
    
    # Return error to client
    response = {
        "error": "Internal Server Error",
        "message": "An unexpected error occurred. Please try again later."
    }
    
    return jsonify(response), 500

# Simple in-memory rate limiting
request_history = {}
RATE_LIMIT = 10  # requests
RATE_WINDOW = 60  # seconds

def rate_limit(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        client_ip = request.remote_addr
        current_time = time.time()
        
        # Clean up old entries
        for ip in list(request_history.keys()):
            request_history[ip] = [t for t in request_history[ip] if current_time - t < RATE_WINDOW]
            if not request_history[ip]:
                del request_history[ip]
        
        # Check rate limit
        if client_ip in request_history and len(request_history[client_ip]) >= RATE_LIMIT:
            app.logger.warning(f"Rate limit exceeded for {client_ip}")
            return jsonify({"error": "Rate limit exceeded. Please try again later."}), 429
        
        # Add current request to history
        if client_ip not in request_history:
            request_history[client_ip] = []
        request_history[client_ip].append(current_time)
        
        return func(*args, **kwargs)
    return wrapper

def validate_url(url):
    """Basic URL validation for EDHRec links"""
    if not url:
        return False
    edhrec_pattern = r'^https?://(?:www\.)?edhrec\.com/commanders/[a-zA-Z0-9-]+'
    return bool(re.match(edhrec_pattern, url))

@app.route('/')
def home():
    app.logger.info("Home page requested")
    try:
        return render_template('index.html')
    except Exception as e:
        app.logger.error(f"Error rendering home page: {str(e)}")
        return f"Error loading page: {str(e)}", 500


@app.route('/underpriced', methods=['GET'])
@rate_limit
def get_underpriced():
    try:
        # Extract and validate query parameters
        threshold = request.args.get('threshold', default=2, type=float)
        if threshold < 0:
            return jsonify({"error": "Threshold cannot be negative"}), 400
            
        # Improved error handling with detailed logging
        app.logger.info(f"Finding underpriced cards with threshold: {threshold}")
        underpriced = underpriced_cards.find_underpriced_cards(threshold=threshold)
        return jsonify(underpriced)
    except Exception as e:
        app.logger.error(f"Error finding underpriced cards: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/update_database', methods=['POST'])
@rate_limit
def update_database():
    """Manual database update endpoint (simplified, runs update script in background)"""
    try:
        # Validate request data
        data = request.json
        if not data:
            return jsonify({"error": "Missing request data"}), 400
            
        db_type = data.get('type')
        if not db_type or db_type not in ['outland', 'scryfall', 'all']:
            return jsonify({"error": "Invalid database type. Must be 'outland', 'scryfall', or 'all'"}), 400
        
        app.logger.info(f"Starting manual database update: {db_type}")
        
        # Run the update script in background
        try:
            # Run the update script as a subprocess (doesn't block)
            subprocess.Popen(
                ["python", "update_databases.py", db_type],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            
            return jsonify({"status": "success", "message": f"Database update ({db_type}) started in background. Check logs for progress."})
            
        except Exception as e:
            app.logger.error(f"Error starting update script: {str(e)}")
            return jsonify({"error": f"Error starting update script: {str(e)}"}), 500
            
    except Exception as e:
        app.logger.error(f"Error in update_database endpoint: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/database_status')
def database_status():
    try:
        # Use utils to get file paths
        data_dir = utils.get_data_dir()
        outland_path = data_dir / 'scraped_cards.json'
        scryfall_path = data_dir / 'card_prices.json'
        commander_path = data_dir / 'LegendaryCreatures.json'
        
        # Check if files exist
        outland_exists = outland_path.exists()
        scryfall_exists = scryfall_path.exists()
        commander_exists = commander_path.exists()
        
        # Log warning for missing files
        if not outland_exists:
            logger.warning(f"Outland card database not found at {outland_path}")
        if not scryfall_exists:
            logger.warning(f"Scryfall price database not found at {scryfall_path}")
        if not commander_exists:
            logger.warning(f"Commander database not found at {commander_path}")
            
        outland_status = {'exists': False, 'last_updated': None, 'card_count': 0}
        scryfall_status = {'exists': False, 'last_updated': None, 'card_count': 0}
        commander_status = {'exists': False, 'last_updated': None, 'card_count': 0}
        
        if outland_exists:
            with open(outland_path, 'r') as f:
                outland_data = json.load(f)
                # Get data from metadata object
                metadata = outland_data.get('metadata', {})
                outland_status = {
                    'exists': True,
                    'last_updated': metadata.get('last_updated', 'Unknown'),
                    'card_count': metadata.get('card_count', 0)
                }
                
        if scryfall_exists:
            with open(scryfall_path, 'r') as f:
                scryfall_data = json.load(f)
                scryfall_status = {
                    'exists': True,
                    'last_updated': scryfall_data.get('last_updated', 'Unknown'),
                    'card_count': scryfall_data.get('card_count', 0)
                }
                
        if commander_exists:
            with open(commander_path, 'r') as f:
                commander_data = json.load(f)
                commander_status = {
                    'exists': True,
                    'last_updated': commander_data.get('last_updated', 'Unknown'),
                    'card_count': len(commander_data.get('commanders', []))
                }
        
        # Calculate days since last update
        now = datetime.now()
        if outland_status['last_updated']:
            try:
                outland_date = datetime.fromisoformat(outland_status['last_updated'])
                outland_status['days_since_update'] = (now - outland_date).days
            except:
                outland_status['days_since_update'] = None
                
        if scryfall_status['last_updated']:
            try:
                scryfall_date = datetime.fromisoformat(scryfall_status['last_updated'])
                scryfall_status['days_since_update'] = (now - scryfall_date).days
            except:
                scryfall_status['days_since_update'] = None
                
        # Get next scheduled database update
        next_update = utils.get_next_sunday_1am()
                
        return jsonify({
            'outland_database': outland_status,
            'scryfall_database': scryfall_status,
            'commander_database': commander_status,
            'next_scheduled_update': next_update.isoformat(),
            'auto_update_enabled': True,
            'database_size': {
                'outland': utils.get_file_size(outland_path) if outland_exists else 0,
                'scryfall': utils.get_file_size(scryfall_path) if scryfall_exists else 0
            }
        })
    except Exception as e:
        app.logger.error(f"Error checking database status: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/health')
def health_check():
    """
    Basic health check endpoint.
    Returns information about the application's health and configuration.
    """
    try:
        # Verify data directories
        data_dir = utils.get_data_dir()
        
        # Check outland data
        outland_data_exists = False
        outland_data_path = data_dir / 'scraped_cards.json'
        
        if outland_data_path.exists():
            outland_data_exists = True
            
        # Check scryfall data
        scryfall_data_exists = False
        scryfall_data_path = data_dir / 'card_prices.json'
        
        if scryfall_data_path.exists():
            scryfall_data_exists = True
        
        # Get next scheduled database update
        next_update = utils.get_next_sunday_1am()
        
        return jsonify({
            'status': 'ok',
            'uptime': 'Unknown',  # Could be implemented if needed
            'outland_database': 'available' if outland_data_exists else 'missing',
            'scryfall_database': 'available' if scryfall_data_exists else 'missing',
            'next_scheduled_update': next_update.isoformat(),
            'environment': os.environ.get('FLASK_ENV', 'production'),
            'database_size': {
                'outland': utils.get_file_size(outland_data_path) if outland_data_exists else 0,
                'scryfall': utils.get_file_size(scryfall_data_path) if scryfall_data_exists else 0
            },
            'logs_configured': True
        })
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        return jsonify({
            'status': 'error',
            'error': str(e)
        }), 500

def ensure_data_directory():
    """Ensure data directory exists and contains necessary files"""
    # Use utils to get and ensure data directory exists
    data_dir = utils.get_data_dir()
    logger.info(f"Using data directory: {data_dir}")
    return str(data_dir)

@app.route('/search_commanders', methods=['GET'])
@rate_limit
def search_commanders():
    try:
        query = request.args.get('q', '').strip().lower()
        if not query or len(query) < 2:
            return jsonify([])
        
        # Normalize query by removing special characters
        normalized_query = re.sub(r'[^a-z0-9\s]', '', query)
        
        # Load legendary creatures data using utils
        legendary_data = utils.load_json_file('LegendaryCreatures.json')
        if not legendary_data:
            logger.error("LegendaryCreatures.json file not found or empty")
            return jsonify([])
        
        # Three categories of matches with different priorities
        exact_matches = []      # Exact match (highest priority)
        starts_with_matches = [] # Starts with query (medium priority)
        contains_matches = []   # Contains query (lowest priority)
        
        # Check if data exists and has 'data' key
        if 'data' in legendary_data:
            for card in legendary_data['data']:
                if 'name' not in card:
                    continue
                    
                card_name = card['name'].lower()
                # Also normalize card name for better matching
                normalized_card_name = re.sub(r'[^a-z0-9\s]', '', card_name)
                
                # Categorize match type (try both original and normalized versions)
                if card_name == query or normalized_card_name == normalized_query:
                    exact_matches.append({
                        'name': card['name'],
                        'id': card.get('id', '')
                    })
                elif card_name.startswith(query) or normalized_card_name.startswith(normalized_query):
                    starts_with_matches.append({
                        'name': card['name'],
                        'id': card.get('id', '')
                    })
                elif query in card_name or normalized_query in normalized_card_name:
                    contains_matches.append({
                        'name': card['name'],
                        'id': card.get('id', '')
                    })
            
            # Sort each category alphabetically
            exact_matches.sort(key=lambda x: x['name'])
            starts_with_matches.sort(key=lambda x: x['name'])
            contains_matches.sort(key=lambda x: x['name'])
            
            # Remove duplicates that might exist across categories
            seen_ids = set()
            unique_commanders = []
            
            for commander in exact_matches + starts_with_matches + contains_matches:
                if commander['id'] not in seen_ids:
                    seen_ids.add(commander['id'])
                    unique_commanders.append(commander)
            
            # Limit to 10 results
            commanders = unique_commanders[:10]
        else:
            commanders = []
        
        return jsonify(commanders)
    except Exception as e:
        app.logger.error(f"Error in search_commanders: {str(e)}")
        return jsonify([])

@app.route('/search_commander', methods=['POST'])
@rate_limit
def search_commander():
    try:
        # Handle invalid JSON
        if not request.is_json:
            return jsonify({"error": "Invalid JSON in request"}), 400
            
        try:
            data = request.get_json()
        except Exception as e:
            return jsonify({"error": f"Invalid JSON format: {str(e)}"}), 400
            
        if data is None:
            return jsonify({"error": "Invalid or empty JSON in request"}), 400
            
        commander_name = data.get('commander_name')
        max_price = float(data.get('max_price', 8))
        limit = int(data.get('limit', 10))
        page = int(data.get('page', 1))
        
        # New debug parameters
        debug = data.get('debug', False)
        debug_card = data.get('debug_card')
        debug_info = {}
        
        if not commander_name:
            return jsonify({"error": "Commander name is required"}), 400
        
        # Find the EDHRec URL for this commander
        edhrec_url = find_edhrec_url(commander_name, max_price)
        
        if not edhrec_url:
            return jsonify({"error": f"Could not find EDHRec page for commander: {commander_name}"}), 404
        
        # Add debug info for EDHRec URL
        if debug:
            debug_info['edhrec_url'] = edhrec_url
            debug_info['budget_option'] = 'budget' if max_price < 50 else ('expensive' if max_price > 100 else 'standard')
            debug_info['max_price'] = max_price
            
            # If a specific debug card was requested, try to find it directly in Outland database
            if debug_card:
                from EDH_search import CardSearch
                searcher = CardSearch()
                
                # Check if the card exists in Outland database
                file_path = utils.get_data_dir() / 'scraped_cards.json'
                
                try:
                    if file_path.exists():
                        with open(file_path, 'r') as file:
                            scraped_data = json.load(file)
                            scraped_cards = scraped_data['cards']
                            
                            # Try exact match
                            debug_card_lower = debug_card.lower().strip()
                            exact_matches = [card for card in scraped_cards if card['name'].lower() == debug_card_lower]
                            
                            # Try partial match
                            partial_matches = [card for card in scraped_cards if debug_card_lower in card['name'].lower()]
                            
                            # Price filtered matches
                            price_filtered = [card for card in exact_matches if card['price'] <= max_price and card['price'] > 0]
                            
                            debug_info['card_debug'] = {
                                'card_name': debug_card,
                                'exists_in_database': len(exact_matches) > 0,
                                'exact_matches_count': len(exact_matches),
                                'partial_matches_count': len(partial_matches),
                                'price_filtered_count': len(price_filtered),
                                'max_price_filter': max_price
                            }
                            
                            if exact_matches:
                                debug_info['card_debug']['exact_matches'] = [{
                                    'name': card['name'],
                                    'price': card['price'],
                                    'link': card.get('store_url', 'No link')
                                } for card in exact_matches[:5]]  # Show up to 5 matches
                    else:
                        debug_info['card_debug'] = {
                            'error': f"Database file not found at {file_path}"
                        }
                            
                except Exception as e:
                    debug_info['card_debug'] = {
                        'error': f"Error while debugging card: {str(e)}"
                    }
        
        # Get recommended cards with pagination
        cards = EDH_search.get_recommended_cards(edhrec_url, max_price, limit, page)
        
        response_data = cards
        
        # If debugging is enabled, include debug information in the response
        if debug:
            response_data = {
                'results': cards,
                'debug_info': debug_info
            }
            
        return jsonify(response_data)
    except Exception as e:
        logger.error(f"Error in search_commander: {str(e)}")
        return jsonify({"error": str(e)}), 500

def find_edhrec_url(commander_name, max_price=None):
    """
    Find the EDHRec URL for a given commander name, with budget options based on max price.
    
    Args:
        commander_name (str): The name of the commander
        max_price (float, optional): Maximum price in NOK. Used to determine budget option.
            - If max_price < 50: use budget URL
            - If max_price > 100: use expensive URL
            - Otherwise: use standard URL
            
    Returns:
        str: The EDHRec URL for the commander, or None if not found
    """
    try:
        # Clean the commander name for URL
        clean_name = commander_name.lower().replace(' ', '-').replace(',', '').replace("'", '')
        
        # Base URL
        base_url = f"https://edhrec.com/commanders/{clean_name}"
        
        # Determine budget option
        budget_suffix = ""
        if max_price is not None:
            if max_price < 50:
                budget_suffix = "/budget"
                logger.info(f"Using budget URL for {commander_name} (max price: {max_price})")
            elif max_price > 100:
                budget_suffix = "/expensive"
                logger.info(f"Using expensive URL for {commander_name} (max price: {max_price})")
        
        # Construct full URL with budget option
        edhrec_url = f"{base_url}{budget_suffix}"
        
        # Verify the URL exists
        response = requests.head(edhrec_url)
        if response.status_code == 200:
            return edhrec_url
        
        # If URL with budget option fails, try base URL
        if budget_suffix:
            logger.warning(f"Budget URL {edhrec_url} not found, trying base URL")
            response = requests.head(base_url)
            if response.status_code == 200:
                return base_url
        
        # If direct URL fails, try searching on EDHRec
        search_url = f"https://edhrec.com/search?q={commander_name}"
        response = requests.get(search_url)
        
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Look for commander links
            commander_links = soup.select('a[href^="/commanders/"]')
            
            if commander_links:
                # Get the first matching commander link
                href = commander_links[0]['href']
                base_url = f"https://edhrec.com{href}"
                # Apply budget suffix to found URL
                return f"{base_url}{budget_suffix}" if budget_suffix else base_url
        
        return None
    except Exception as e:
        logger.error(f"Error finding EDHRec URL: {str(e)}")
        return None

if __name__ == '__main__':
    # Ensure data directory exists
    data_dir = ensure_data_directory()
    app.logger.info(f"Application starting with data directory: {data_dir}")
    
    # Start the Flask app
    app.run(host='0.0.0.0', port=5000, debug=True) 