import json
import os
import requests
from bs4 import BeautifulSoup
from colorama import Fore, Style
import time
import log_config
import traceback
import utils
from pathlib import Path

# Configure logger for this module
logger = log_config.get_logger(__name__, 'edh_search.log')

class CardSearch:
    def search_outland(self, card_name, max_price):
        try:
            # Use utils to get the data file path
            file_path = utils.get_data_dir() / 'scraped_cards.json'
            
            if not file_path.exists():
                logger.error(f"Error: scraped_cards.json not found at {file_path}. Please run the Outland database update first.")
                return None
                
            with open(file_path, 'r') as file:
                scraped_cards = json.load(file)
                scraped_cards = scraped_cards['cards']
                
        except FileNotFoundError:
            logger.error(f"Error: scraped_cards.json not found at {file_path}. Please run the Outland database update first.")
            return None
        except json.JSONDecodeError:
            logger.error(f"Error: scraped_cards.json is corrupted or empty.")
            return None

        # Clean up the search name
        search_name = card_name.lower().strip()
        
        # Additional debugging for specific cards (e.g., Svella)
        is_debug_card = search_name == "svella, ice shaper"
        if is_debug_card:
            logger.debug(f"===== DEBUG: Searching for {card_name} =====")
            logger.debug(f"Max price: {max_price} NOK")
            logger.debug(f"Search name (cleaned): '{search_name}'")
            logger.debug(f"Total cards in database: {len(scraped_cards)}")
            
            # Find all variants of the card regardless of price
            all_variants = [card for card in scraped_cards if card['name'].lower() == search_name]
            partial_matches = [card for card in scraped_cards if search_name in card['name'].lower()]
            
            logger.debug(f"Exact name matches (any price): {len(all_variants)}")
            logger.debug(f"Partial name matches: {len(partial_matches)}")
            
            if all_variants:
                logger.debug("Available variants:")
                for i, card in enumerate(all_variants):
                    logger.debug(f"  {i+1}. {card['name']} - {card['price']} NOK - URL: {card.get('store_url', 'No URL')}")
            
            if partial_matches and not all_variants:
                logger.debug("Partial matches:")
                for i, card in enumerate(partial_matches[:5]):  # Show up to 5 partial matches
                    logger.debug(f"  {i+1}. {card['name']} - {card['price']} NOK")
        
        # Try exact match first
        found_cards = [card for card in scraped_cards if
                      card['name'].lower() == search_name and 
                      card['price'] <= max_price and 
                      card['price'] > 0]
        
        if is_debug_card:
            logger.debug(f"Exact matches within price range ({max_price} NOK): {len(found_cards)}")
            
            # Log any cards that matched the name but were filtered out by price
            price_filtered_out = [card for card in scraped_cards if
                                card['name'].lower() == search_name and 
                                (card['price'] > max_price or card['price'] <= 0)]
            
            if price_filtered_out:
                logger.debug("Cards filtered out by price:")
                for i, card in enumerate(price_filtered_out):
                    logger.debug(f"  {i+1}. {card['name']} - {card['price']} NOK (excluded because price > {max_price} or price <= 0)")
        

        if found_cards:
            # Sort by price to get the cheapest option
            found_cards.sort(key=lambda x: x['price'])
            found_card = found_cards[0]
            logger.debug(f"Found card: {found_card['name']} at {found_card['price']} NOK")
            return {
                'name': found_card['name'],
                'price': found_card['price'],
                'image_url': found_card.get('image_url', ''),
                'store_url': found_card['store_url'],
            }
        
        logger.debug(f"No card found for: {card_name}")
        if is_debug_card:
            logger.debug("===== END DEBUG =====")
        return None

    # Scrapes edh using an url and returns a list of synergistic cards
    def scrape_edh(self, url):
        try:
            logger.info(f"Starting EDH scrape for URL: {url}")
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            
            logger.info("Fetching page...")
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Try different possible class names for card containers
            possible_card_classes = [
                'Card_container__Ng56K',
                'Card_container',
                'card-container',
                'CardView',  # Add more potential class names
                'recommendation-tile'
            ]
            
            card_wrappers = []
            for class_name in possible_card_classes:
                card_wrappers = soup.find_all(['div', 'article'], class_=lambda x: x and class_name in x)
                if card_wrappers:
                    logger.info(f"Found {len(card_wrappers)} cards using class: {class_name}")
                    break
            
            if not card_wrappers:
                logger.warning("No card wrappers found. Trying alternative methods...")
                # Try finding cards by data attributes or other methods
                card_wrappers = soup.find_all(['div', 'article'], {'data-component': 'card'})
                if not card_wrappers:
                    card_wrappers = soup.find_all(['div', 'article'], {'data-card-id': True})
            
            if not card_wrappers:
                logger.error("Could not find any card elements on the page")
                return []

            card_list = []
            for card_wrapper in card_wrappers:
                # Try to find card name in multiple ways
                card_name = None
                for selector in ['h3', 'span', 'div', 'a']:
                    name_elem = card_wrapper.find(selector, class_=lambda x: x and any(term in x.lower() for term in ['name', 'title', 'header']))
                    if name_elem:
                        card_name = name_elem.get_text(strip=True)
                        break

                if not card_name:
                    # Try finding any text that looks like a card name
                    texts = [text for text in card_wrapper.stripped_strings 
                            if len(text) > 3 and not text.startswith('+') 
                            and not text.endswith('%') and not text.startswith('$')]
                    if texts:
                        card_name = texts[0]

                if card_name:
                    # Convert print to debug level since it's verbose and frequent
                    logger.debug(f"Found card: {card_name}")
                    card_info = {'name': card_name}
                    
                    # Try to find synergy percentage
                    synergy_text = None
                    for elem in card_wrapper.find_all(['div', 'span']):
                        text = elem.get_text(strip=True)
                        if '+' in text and '%' in text:
                            synergy_text = text
                            break
                    
                    if synergy_text:
                        try:
                            synergy = synergy_text.split('+')[1].split('%')[0].strip()
                            card_info['synergy_percentage'] = synergy
                            # print(f"{Fore.BLUE}Synergy: {synergy}%{Style.RESET_ALL}")
                        except:
                            card_info['synergy_percentage'] = '0'
                    else:
                        card_info['synergy_percentage'] = '0'
                    
                    card_list.append(card_info)

            logger.info(f"Successfully found {len(card_list)} cards")
            return card_list

        except Exception as e:
            logger.error(f"Error during EDH scrape: {str(e)}")
            logger.debug(traceback.format_exc())
            return []

    def scrape_tcgplayer(self, url):
        card_list = []

        response = requests.get(url)

        if response.status_code == 200:
            soup = BeautifulSoup(response.content, 'html.parser')
            card_names = soup.find_all('span', class_='subdeck-group__card-name')

            if card_names:
                for name in card_names:
                    card_list.append(name.text.strip())
            else:
                logger.error("No card names found on the website using the provided structure.")
        else:
            logger.error("Failed to retrieve data from the website.")

        return card_list
    
def get_recommended_cards(edhrec_url, max_price, limit, page=1):
    """
    Get recommended cards for a commander from EDHRec and find them on Outland.
    
    Args:
        edhrec_url (str): The EDHRec URL for the commander
        max_price (float): Maximum price in NOK
        limit (int): Maximum number of cards per page
        page (int): Page number (1-indexed)
        
    Returns:
        list: List of card dictionaries with name, price, synergy, and store_url
    """
    searcher = CardSearch()
    
    # Cache the commander recommendations to avoid re-scraping for pagination
    # Use a simple caching mechanism with a global variable
    global _commander_rec_cache
    global _commander_url_cache
    
    if not hasattr(get_recommended_cards, '_commander_rec_cache'):
        get_recommended_cards._commander_rec_cache = {}
        get_recommended_cards._commander_url_cache = None
    
    # If we're requesting a new commander, clear the cache and scrape
    if edhrec_url != get_recommended_cards._commander_url_cache:
        get_recommended_cards._commander_url_cache = edhrec_url
        get_recommended_cards._commander_rec_cache = {}
        commander_rec = searcher.scrape_edh(edhrec_url)
    else:
        # Use cached results if available
        commander_rec = get_recommended_cards._commander_rec_cache.get('all_cards')
    
    # If we don't have cached results yet, store them
    if 'all_cards' not in get_recommended_cards._commander_rec_cache:
        get_recommended_cards._commander_rec_cache['all_cards'] = commander_rec
    
    # Calculate pagination
    start_idx = (page - 1) * limit
    end_idx = start_idx + limit
    
    # Get all matching cards first (if not already cached)
    if f'matching_cards_{max_price}' not in get_recommended_cards._commander_rec_cache:
        all_matching_cards = []
        for card in commander_rec:
            found_card = searcher.search_outland(card['name'], max_price=max_price)
            if found_card:
                found_card['synergy'] = card.get('synergy_percentage', '0')
                all_matching_cards.append(found_card)
        
        # Sort by synergy (highest first)
        all_matching_cards.sort(key=lambda x: float(x['synergy']), reverse=True)
        get_recommended_cards._commander_rec_cache[f'matching_cards_{max_price}'] = all_matching_cards
    
    # Get the paginated results
    all_matching_cards = get_recommended_cards._commander_rec_cache[f'matching_cards_{max_price}']
    paginated_results = all_matching_cards[start_idx:end_idx]
    
    return paginated_results
    
    