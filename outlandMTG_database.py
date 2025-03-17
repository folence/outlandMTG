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

async def fetch_page(session: aiohttp.ClientSession, url: str, page: int, semaphore: Semaphore) -> tuple[int, str]:
    """Fetch a page with rate limiting and retry logic"""
    current_backoff = INITIAL_BACKOFF
    retries = 0
    
    async with semaphore:  # Control concurrent requests
        while retries <= MAX_RETRIES:
            try:
                # Add random delay between 1-3 seconds before each request to avoid detection
                await asyncio.sleep(1 + random.random() * 2)
                
                # Use a rotating set of user agents to avoid being blocked
                user_agents = [
                    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.1 Safari/605.1.15',
                    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:89.0) Gecko/20100101 Firefox/89.0',
                    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.212 Safari/537.36'
                ]
                
                # Use a different user agent for each request
                headers = {
                    'User-Agent': random.choice(user_agents),
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                    'Accept-Language': 'en-US,en;q=0.5',
                    'Connection': 'keep-alive',
                    'Upgrade-Insecure-Requests': '1',
                    'Cache-Control': 'max-age=0'
                }
                
                async with session.get(url, headers=headers, timeout=30) as response:
                    if response.status == 200:
                        html = await response.text()
                        logger.info(f"Successfully fetched page {page}")
                        return page, html
                    elif response.status == 429:
                        retries += 1
                        # Add jitter to backoff time to avoid synchronized retries
                        jitter_amount = random.uniform(1 - JITTER, 1 + JITTER)
                        wait_time = current_backoff * jitter_amount
                        
                        print(f"⚠️ Rate limited on page {page}, retry {retries}/{MAX_RETRIES}, waiting {wait_time:.1f}s...")
                        logger.warning(f"Rate limited on page {page}, retry {retries}/{MAX_RETRIES}, waiting {wait_time:.1f}s...")
                        await asyncio.sleep(wait_time)
                        
                        # Exponential backoff
                        current_backoff = min(current_backoff * BACKOFF_FACTOR, MAX_BACKOFF)
                        
                        # If not the last retry, continue with the loop
                        if retries <= MAX_RETRIES:
                            continue
                        
                        return page, ""
                    else:
                        print(f"❌ Page {page} returned status {response.status}")
                        logger.warning(f"Page {page} returned status {response.status}")
                        retries += 1
                        await asyncio.sleep(current_backoff)
                        current_backoff = min(current_backoff * BACKOFF_FACTOR, MAX_BACKOFF)
            except asyncio.TimeoutError:
                print(f"⚠️ Timeout fetching page {page}, retry {retries}/{MAX_RETRIES}")
                logger.warning(f"Timeout fetching page {page}, retry {retries}/{MAX_RETRIES}")
                retries += 1
                await asyncio.sleep(current_backoff)
                current_backoff = min(current_backoff * BACKOFF_FACTOR, MAX_BACKOFF)
            except Exception as e:
                print(f"❌ Error fetching page {page}: {str(e)}")
                logger.error(f"Error fetching page {page}: {str(e)}")
                retries += 1
                await asyncio.sleep(current_backoff)
                current_backoff = min(current_backoff * BACKOFF_FACTOR, MAX_BACKOFF)
            
        logger.error(f"Failed to fetch page {page} after {MAX_RETRIES} retries")
        return page, ""

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
    
    print(f"💾 Saved checkpoint: Page {page}, {len(cards)} cards")
    logger.info(f"Saved checkpoint: Page {page}, {len(cards)} cards, {len(completed_pages)} completed pages")

def load_checkpoint() -> Tuple[int, Set[int]]:
    """Load checkpoint if it exists, otherwise return starting values"""
    current_page = 1
    completed_pages = set()
    
    # Load page checkpoint
    checkpoint = utils.load_pickle_file(CHECKPOINT_FILE)
    if checkpoint:
        current_page = checkpoint.get('page', 1)
        print(f"📋 Loaded checkpoint from page {current_page}")
        logger.info(f"Loaded checkpoint from {checkpoint.get('timestamp')}")
    
    # Load completed pages
    completed_pages_data = utils.load_pickle_file(COMPLETED_PAGES_FILE)
    if completed_pages_data:
        completed_pages = completed_pages_data
        print(f"📋 Loaded {len(completed_pages)} completed pages from previous run")
        logger.info(f"Loaded {len(completed_pages)} completed pages from previous run")
    
    return current_page, completed_pages

def load_partial_results() -> List[Dict[str, Any]]:
    """Load partial results if they exist"""
    partial_results = utils.load_json_file(PARTIAL_RESULTS_FILE)
    
    if partial_results:
        cards = partial_results.get('cards', [])
        print(f"📋 Loaded {len(cards)} cards from partial results")
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
                print(f"⏩ Skipping page {page} - already processed")
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
                    print(f"⚠️ Failed to fetch {consecutive_empty_pages} consecutive pages, pausing scraping")
                    logger.warning(f"Failed to fetch {consecutive_empty_pages} consecutive pages, pausing scraping")
                    await asyncio.sleep(10)
                    consecutive_empty_pages = 0
                
                continue
                
            # Reset counter on successful page
            consecutive_empty_pages = 0
                
            soup = BeautifulSoup(html, 'html.parser')
            card_entries = soup.find_all('li', class_='item product product-item')
            
            if not card_entries:
                print(f"⚠️ No cards found on page {page}")
                logger.warning(f"No cards found on page {page}")
                should_continue = False
                break

            # Track in-stock status for this page
            total_cards = len(card_entries)
            out_of_stock_count = 0
                
            print(f"🔍 Processing page {page}: Found {total_cards} cards")
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
                print(f"⚠️ Stopping at page {page}: High number of out-of-stock cards ({out_of_stock_ratio:.1%})")
                logger.warning(f"Stopping at page {page}: High number of out-of-stock cards ({out_of_stock_ratio:.1%})")
                should_continue = False
                break
    
    return all_cards, should_continue

async def main(status_callback=None):
    """Main entry point for the scraper"""
    start_time = time.time()
    print("Starting Outland MTG scraper...")
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
        print(f"📋 Resuming scrape from page {current_page} with {len(cards)} existing cards")
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
            
            print(f"🔍 Processing batch starting at page {current_page}")
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
                print(f"✅ Found {len(batch_cards)} new cards in batch, total: {len(cards)}")
                failed_batches = 0  # Reset failed batch counter on success
                
                # Save checkpoint periodically
                if batch_count % checkpoint_interval == 0:
                    save_checkpoint(current_page, cards, completed_pages)
            else:
                failed_batches += 1
                print(f"⚠️ Batch starting at page {current_page} returned no cards")
                logger.warning(f"Batch starting at page {current_page} returned no cards")
                
                # If we have consecutive failed batches, take a longer break
                if failed_batches >= 3:
                    print(f"⚠️ Multiple consecutive failed batches, taking a longer break")
                    logger.warning("Multiple consecutive failed batches, taking a longer break")
                    await asyncio.sleep(30)  # Take a longer break
                    failed_batches = 0
            
            current_page += batch_size
            
            # Limit to 50 batches to prevent infinite loop
            if current_page > 250:
                print("🛑 Reached maximum page limit")
                logger.info("Reached maximum page limit")
                break
    except KeyboardInterrupt:
        print("\n⚠️ Scraper interrupted by user, saving progress...")
        logger.warning("Scraper interrupted by user, saving progress...")
        # Save checkpoint on interrupt
        save_checkpoint(current_page, cards, completed_pages)
    except Exception as e:
        print(f"❌ Error during scraping: {str(e)}")
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
    print(f"💾 Saving {len(cards)} unique cards to database...")
    utils.save_json_with_metadata(cards, 'scraped_cards.json')
    
    elapsed_time = time.time() - start_time
    minutes, seconds = divmod(elapsed_time, 60)
    
    completion_message = f"Scraping completed in {int(minutes)}m {int(seconds)}s. Found {len(cards)} unique cards"
    print(f"✅ {completion_message}")
    logger.info(completion_message)
    
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
        print("Starting Outland database scraper")
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
        print(f"❌ Error in scraper: {str(e)}")
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