import json
import os
import log_config
import utils
from pathlib import Path

# Configure logger for this module
logger = log_config.get_logger(__name__, 'underpriced_cards.log')

def load_json(file_path):
    """Load a JSON file from the data directory or a direct path."""
    # Convert to Path object if it's a string
    if isinstance(file_path, str):
        file_path = utils.get_data_dir() / file_path
    
    logger.info(f"Loading data from: {file_path}")
    
    try:
        with open(file_path, 'r') as file:
            return json.load(file)
    except FileNotFoundError:
        logger.error(f"File not found: {file_path}")
        raise
    except json.JSONDecodeError:
        logger.error(f"Invalid JSON in file: {file_path}")
        raise

def find_underpriced_cards(scryfall_data_path=None, outland_data_path=None, threshold=2):
    # Set default paths
    data_dir = utils.get_data_dir()
    if not scryfall_data_path:
        scryfall_data_path = data_dir / "card_prices.json"
    if not outland_data_path:
        outland_data_path = data_dir / "scraped_cards.json"
        
    logger.info(f"Finding underpriced cards using Scryfall data: {scryfall_data_path}")
    logger.info(f"Finding underpriced cards using Outland data: {outland_data_path}")
    
    scryfall_data = load_json(scryfall_data_path)
    outland_data = load_json(outland_data_path)

    underpriced_cards = []

    for outland_card in outland_data['cards']:
        card_name = outland_card['name']
        card_price_nok = outland_card['price']

        lowest_scryfall_price = float('inf')

        # Check if the card exists in Scryfall data and find the lowest Scryfall price
        for card in scryfall_data['cards']:
            if card['name'] == card_name:
                # Update lowest price using USD if available
                if card['prices']['usd'] and float(card['prices']['usd']) < lowest_scryfall_price:
                    lowest_scryfall_price = float(card['prices']['usd'])

                # Update lowest price using EUR if available
                if card['prices']['eur'] and float(card['prices']['eur']) * 1.05 < lowest_scryfall_price:
                    lowest_scryfall_price = float(card['prices']['eur']) * 1.05

        # Convert NOK to USD using a specific conversion rate
        converted_price_usd = card_price_nok * 0.09

        # Calculate the price difference in USD
        price_difference = lowest_scryfall_price - converted_price_usd

        # Check if the Outland price is significantly lower
        if price_difference > threshold and price_difference != float('inf') and card_price_nok > 5:
            underpriced_cards.append({
                'name': card_name,
                'price_difference_usd': price_difference,
                'outland_price_nok': card_price_nok,
                'lowest_scryfall_price_usd': lowest_scryfall_price,
                'store_url': outland_card['store_url']
            })

    # Sort by price difference
    underpriced_cards.sort(key=lambda x: x['price_difference_usd'])
    
    
    # Display or further process the most underpriced cards
    for card in underpriced_cards:
        logger.info("-" * 30)
        logger.info(f"Name: {card['name']}")
        logger.info(f"Outland Price (NOK): {card['outland_price_nok']}")
        logger.info(f"Scryfall Price (USD): {card['lowest_scryfall_price_usd']}")
        logger.info(f"Price Difference (USD): {card['price_difference_usd']}")
        logger.info(f"Store URL: {card['store_url']}")
        logger.info("-" * 30)

    logger.info(f"Found {len(underpriced_cards)} underpriced cards with threshold {threshold}")
    return underpriced_cards
