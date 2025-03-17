import aiohttp
from bs4 import BeautifulSoup
import re
import asyncio
import json
from colorama import Fore, Style
import time
import random
from typing import List, Dict, Any, Optional, Tuple, Set
from asyncio import Semaphore
from datetime import datetime
import os
import hashlib
import log_config
import traceback
import utils
from pathlib import Path

# Configure logger for this module
logger = log_config.get_logger(__name__, 'outlandMTG_database.log')

# Constants for rate limiting
MAX_RETRIES = 5
INITIAL_BACKOFF = 5
MAX_BACKOFF = 60
BACKOFF_FACTOR = 2
JITTER = 0.5  # Random jitter factor to avoid synchronized retries

# Constants for storage
CHECKPOINT_FILE = 'scraper_checkpoint.pkl'
COMPLETED_PAGES_FILE = 'completed_pages.pkl'
PARTIAL_RESULTS_FILE = 'partial_results.json'

def clean_card_name(name: str) -> str:
    """Clean up card name by removing suffixes and extra spaces"""
    return utils.clean_card_name(name)

def extract_price(price_text: str) -> int:
    """Extract price from price text, handling different formats"""
    try:
        # Remove all non-digit characters except comma and period
        price_clean = re.sub(r'[^\d,.]', '', price_text)
        # Replace comma with period for decimal
        price_clean = price_clean.replace(',', '.')
        # Convert to float (in NOK) and then to integer (øre)
        return int(float(price_clean) * 100)
    except Exception as e:
        logger.error(f"Error parsing price '{price_text}': {str(e)}")
        return 0

def save_checkpoint(page: int, cards: List[Dict[str, Any]], completed_pages: Set[int]):
    """Save current state to a checkpoint file"""
    # Save current page and timestamp
    utils.save_pickle_file({'page': page, 'timestamp': datetime.now().isoformat()}, CHECKPOINT_FILE)
    
    # Save completed pages
    utils.save_pickle_file(completed_pages, COMPLETED_PAGES_FILE)
    
    # Save partial results as JSON
    partial_results = {
        'cards': cards,
        'count': len(cards),
        'last_updated': datetime.now().isoformat()
    }
    utils.save_json_file(partial_results, PARTIAL_RESULTS_FILE)
    
    logger.info(f"Saved checkpoint: Page {page}, {len(cards)} cards, {len(completed_pages)} completed pages")

def load_checkpoint() -> Tuple[int, Set[int]]:
    """Load checkpoint if it exists, otherwise return starting values"""
    current_page = 1
    completed_pages = set()
    
    # Load page checkpoint
    checkpoint = utils.load_pickle_file(CHECKPOINT_FILE)
    if checkpoint:
        current_page = checkpoint.get('page', 1)
        logger.info(f"Loaded checkpoint from {checkpoint.get('timestamp')}")
    
    # Load completed pages
    completed_pages_data = utils.load_pickle_file(COMPLETED_PAGES_FILE)
    if completed_pages_data:
        completed_pages = completed_pages_data
        logger.info(f"Loaded {len(completed_pages)} completed pages from previous run")
    
    return current_page, completed_pages

def load_partial_results() -> List[Dict[str, Any]]:
    """Load partial results if they exist"""
    partial_results = utils.load_json_file(PARTIAL_RESULTS_FILE)
    
    if partial_results:
        cards = partial_results.get('cards', [])
        logger.info(f"Loaded {len(cards)} cards from partial results")
        return cards
    
    return []

async def process_batch(start: int, end: int, semaphore: Semaphore, cards_seen: Set[str], 
                        completed_pages: Set[int], status_callback=None) -> tuple[List[Dict[str, Any]], bool]:
    """Process a batch of pages and return all found cards"""
    all_cards = []
    should_continue = True
    
    # Keep track of consecutive empty pages
    consecutive_empty_pages = 0
    
    async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=60)) as session:
        # Set a reasonable limit based on your needs
        max_pages = 200  # Limit to maximum 200 pages to avoid excessive requests
        
        for page in range(start, min(end, start + max_pages)):
            # Skip already completed pages
            if page in completed_pages:
                logger.info(f"Skipping page {page} - already processed in previous run")
                if status_callback:
                    status_callback(details=f"Skipping page {page} - already processed")
                continue
                
            if status_callback:
                progress = int((page - start) / min(max_pages, end - start) * 100)
                status_callback(
                    progress=progress,
                    details=f"Processing page {page} of catalog"
                )
                
            url = f"https://www.outland.no/samlekort-og-kortspill/magic-the-gathering/singles?p={page}&product_list_limit=96"
            page_num, html = await fetch_page(session, url, page, semaphore)
            
            if not html:
                if status_callback:
                    status_callback(details=f"Failed to fetch page {page}")
                
                # If we fail three consecutive pages, assume there's a persistent problem
                consecutive_empty_pages += 1
                if consecutive_empty_pages >= 3:
                    logger.warning(f"Failed to fetch {consecutive_empty_pages} consecutive pages, pausing scraping")
                    await asyncio.sleep(10)
                    consecutive_empty_pages = 0
                
                continue
                
            # Reset counter on successful page
            consecutive_empty_pages = 0
                
            soup = BeautifulSoup(html, 'html.parser')
            card_entries = soup.find_all('li', class_='item product product-item')
            
            if not card_entries:
                logger.warning(f"No cards found on page {page}")
                should_continue = False
                break

            # Track in-stock status for this page
            total_cards = len(card_entries)
            out_of_stock_count = 0
                
            logger.info(f"Processing page {page}: Found {total_cards} cards")

            for card in card_entries:
                try:
                    # Updated out-of-stock detection
                    # First check for the text directly
                    is_out_of_stock = False
                    stock_text = card.get_text()
                    if "Ikke på lager" in stock_text:
                        out_of_stock_count += 1
                        continue

                    # Also check for the specific format element
                    if card.find('div', class_='format'):
                        format_text = card.find('div', class_='format').get_text(strip=True)
                        if format_text == "Løskort" and "Ikke på lager" in stock_text:
                            out_of_stock_count += 1
                            continue

                    card_name_element = card.find('a', class_='product-item-link')
                    if not card_name_element:
                        continue
                    
                    card_name = utils.clean_card_name(card_name_element.text)
                    if card_name in cards_seen:
                        continue
                    cards_seen.add(card_name)
                    
                    card_data = {
                        'name': card_name,
                        'price': 0,
                        'store_url': 'N/A',
                        'image_url': ''
                    }
                    
                    if price_elem := card.find('span', class_='price'):
                        # Extract price
                        price_text = price_elem.text.strip()
                        card_data['price'] = utils.extract_price(price_text)
                    
                    if photo_link := card.find('a', class_='product-item-photo'):
                        card_data['store_url'] = photo_link.get('href', '')
                        if img := photo_link.find('img', class_='product-image-photo'):
                            card_data['image_url'] = img.get('src', '')
                    
                    if card_data['price'] > 0:
                        all_cards.append(card_data)
                        
                except Exception as e:
                    logger.error(f"Error processing card: {str(e)}")
                    continue

            # Mark this page as completed
            completed_pages.add(page)

            # Make the out-of-stock detection more sensitive
            out_of_stock_ratio = out_of_stock_count / total_cards if total_cards > 0 else 0
            logger.info(f"Page {page}: {out_of_stock_count}/{total_cards} cards out of stock ({out_of_stock_ratio:.2%})")
            
            # If we find a page that's mostly out of stock (50% or more), we're probably at the end
            if out_of_stock_ratio > 0.5: 
                logger.warning(f"Stopping at page {page}: High number of out-of-stock cards ({out_of_stock_ratio:.1%})")
                should_continue = False
                break
    
    return all_cards, should_continue

async def main(status_callback=None):
    """Main entry point for the scraper"""
    start_time = time.time()
    logger.info("Starting Outland MTG scraper...")
    
    if status_callback:
        status_callback(
            message="Starting scraper", 
            progress=0,
            details="Initializing scraper"
        )
    
    # Load previously saved data if available
    current_page, completed_pages = load_checkpoint()
    cards = load_partial_results()
    cards_seen = set(card['name'] for card in cards)
    
    # Report on loaded data
    if cards:
        logger.info(f"Resuming scrape from page {current_page} with {len(cards)} existing cards")
        if status_callback:
            status_callback(
                message=f"Resuming scrape from page {current_page}",
                details=f"Loaded {len(cards)} existing cards from previous run"
            )
    
    # Reduce concurrent requests to avoid triggering rate limits
    semaphore = Semaphore(2)  # Limit concurrent requests to 2
    
    # Process pages in batches
    batch_size = 5
    keep_going = True
    
    # Track failed batches for adaptive batch size
    failed_batches = 0
    
    checkpoint_interval = 2  # Save checkpoint every N batches
    batch_count = 0
    
    try:
        while keep_going:
            batch_count += 1
            
            if status_callback:
                status_callback(
                    message=f"Processing batch starting at page {current_page}",
                    details=f"Starting batch from page {current_page} to {current_page + batch_size - 1}"
                )
                
            # Add delay between batches to be nice to the server
            await asyncio.sleep(5)
            
            batch_cards, keep_going = await process_batch(
                current_page, 
                current_page + batch_size, 
                semaphore, 
                cards_seen,
                completed_pages,
                status_callback
            )
            
            if batch_cards:
                cards.extend(batch_cards)
                failed_batches = 0  # Reset failed batch counter on success
                
                # Save checkpoint periodically
                if batch_count % checkpoint_interval == 0:
                    save_checkpoint(current_page, cards, completed_pages)
            else:
                failed_batches += 1
                logger.warning(f"Batch starting at page {current_page} returned no cards")
                
                # If we have consecutive failed batches, take a longer break
                if failed_batches >= 3:
                    logger.warning("Multiple consecutive failed batches, taking a longer break")
                    await asyncio.sleep(30)  # Take a longer break
                    failed_batches = 0
            
            current_page += batch_size
            
            # Limit to 50 batches to prevent infinite loop
            if current_page > 250:
                logger.info("Reached maximum page limit")
                break
    except KeyboardInterrupt:
        logger.warning("Scraper interrupted by user, saving progress...")
        # Save checkpoint on interrupt
        save_checkpoint(current_page, cards, completed_pages)
    except Exception as e:
        logger.error(f"Error during scraping: {str(e)}")
        logger.debug(traceback.format_exc())
        # Save checkpoint on error
        save_checkpoint(current_page, cards, completed_pages)
        raise
    
    # Final save
    save_checkpoint(current_page, cards, completed_pages)
    
    # Sort cards by name
    cards.sort(key=lambda x: x['name'])
    
    # Save results to file with metadata
    utils.save_json_with_metadata(cards, 'scraped_cards.json')
    
    elapsed_time = time.time() - start_time
    minutes, seconds = divmod(elapsed_time, 60)
    
    logger.info(f"Scraping completed in {int(minutes)}m {int(seconds)}s. Found {len(cards)} unique cards")
    logger.info(f"Found {len(cards)} unique cards")
    
    if status_callback:
        status_callback(
            message=f"Scraping completed. Found {len(cards)} unique cards in {int(minutes)}m {int(seconds)}s",
            progress=100,
            details="Scraping operation complete"
        )
    
    return cards

def run_scraper(status_callback=None):
    """Run the scraper from a synchronous context"""
    try:
        if status_callback:
            status_callback(message="Starting Outland database scraper", progress=0)
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        result = loop.run_until_complete(main(status_callback))
        loop.close()
        
        if status_callback:
            status_callback(
                message=f"Completed scraping {len(result)} cards",
                progress=100
            )
        
        return result
    except Exception as e:
        logger.error(f"Error in scraper: {str(e)}")
        logger.debug(traceback.format_exc())
        if status_callback:
            status_callback(
                status="failed",
                message=f"Error in scraper: {str(e)}"
            )
        raise

if __name__ == "__main__":
    run_scraper()