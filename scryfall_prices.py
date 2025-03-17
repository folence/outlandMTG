import requests
import json
from datetime import datetime
import os
import time
import log_config
import utils
from pathlib import Path

# Configure logger for this module
logger = log_config.get_logger(__name__, 'scryfall_prices.log')

def fetch_cards_over_one_dollar(status_callback=None):
    """
    Fetch cards with USD price over $1 from Scryfall API.
    
    Args:
        status_callback: Optional callback for progress updates
        
    Returns:
        List[Dict]: List of card dictionaries with name and prices
    """
    if status_callback:
        status_callback(message="Starting Scryfall price fetch", progress=0, details="Initializing")
        
    url = 'https://api.scryfall.com/cards/search?q=usd>0.1'
    cards_over_one_dollar = []
    total_pages = 0
    current_page = 0

    # Fetching data from Scryfall in pages
    has_more = True
    next_page = url
    
    start_time = time.time()

    try:
        while has_more:
            if status_callback:
                status_callback(
                    message=f"Fetching page {current_page + 1} from Scryfall", 
                    details=f"Downloading card data from API"
                )
                
            response = requests.get(next_page)
            
            if response.status_code == 200:
                data = response.json()
                
                # Update total pages if this is the first request
                if current_page == 0 and 'total_cards' in data:
                    total_cards = data.get('total_cards', 0)
                    total_pages = (total_cards // 175) + 1  # Scryfall returns ~175 cards per page
                    if status_callback:
                        status_callback(details=f"Found {total_cards} total cards, approximately {total_pages} pages")
                
                current_page += 1
                
                # Calculate progress if we know total pages
                if total_pages > 0 and status_callback:
                    progress = min(int((current_page / total_pages) * 90), 90)  # Cap at 90% for post-processing
                    status_callback(progress=progress)
                
                cards = [
                    {
                        'name': card['name'],
                        'prices': card.get('prices', {})
                    }
                    for card in data.get('data', [])
                ]
                
                # Filter cards with USD prices over $1
                for card in cards:
                    if 'usd' in card['prices'] and card['prices']['usd'] is not None:
                        if float(card['prices']['usd']) > 1.0:
                            cards_over_one_dollar.append(card)

                # Check if there are more pages
                has_more = data.get('has_more', False)
                next_page = data.get('next_page')
                
                if status_callback:
                    status_callback(details=f"Processed page {current_page}, found {len(cards_over_one_dollar)} cards over $1 so far")
                
                # Sleep to avoid rate limiting
                time.sleep(0.1)
            else:
                error_msg = f"Error fetching data from Scryfall: HTTP {response.status_code}"
                logger.error(error_msg)
                if status_callback:
                    status_callback(details=error_msg)
                    
                # Wait longer if rate limited
                if response.status_code == 429:
                    if status_callback:
                        status_callback(details="Rate limited by Scryfall API, waiting 1 second")
                    time.sleep(1)
                    continue
                else:
                    break

        # Create metadata structure
        if status_callback:
            status_callback(message="Saving card data", progress=95, details="Creating JSON file")
            
        # Save the data with metadata using utils
        metadata = {
            "last_updated": datetime.now().isoformat(),
            "card_count": len(cards_over_one_dollar),
            "cards": cards_over_one_dollar
        }
        
        # Save to JSON file
        output_file = 'card_prices.json'
        utils.save_json_file(metadata, output_file)
        
        logger.info(f"Saved {len(cards_over_one_dollar)} cards to {utils.get_data_dir() / output_file}")
            
        elapsed_time = time.time() - start_time
        minutes, seconds = divmod(elapsed_time, 60)
        
        completion_message = f"Saved {len(cards_over_one_dollar)} cards in {int(minutes)}m {int(seconds)}s"
        logger.info(completion_message)
        
        if status_callback:
            status_callback(
                message=completion_message,
                progress=100,
                details="Scryfall data fetch complete"
            )

        return cards_over_one_dollar
        
    except Exception as e:
        error_message = f"Error fetching Scryfall data: {str(e)}"
        logger.error(error_message)
        if status_callback:
            status_callback(status="failed", message=error_message)
        raise