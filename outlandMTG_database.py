import aiohttp
from bs4 import BeautifulSoup
import re
import asyncio
import json
from colorama import Fore, Style
import time
from typing import List, Dict, Any
from asyncio import Semaphore
from datetime import datetime

async def fetch_page(session: aiohttp.ClientSession, url: str, page: int, semaphore: Semaphore) -> tuple[int, str]:
    """Fetch a page with rate limiting"""
    async with semaphore:  # Control concurrent requests
        try:
            async with session.get(url) as response:
                if response.status == 200:
                    html = await response.text()
                    return page, html
                elif response.status == 429:
                    print(f"{Fore.YELLOW}Rate limited on page {page}, waiting...{Style.RESET_ALL}")
                    await asyncio.sleep(5)  # Wait 5 seconds on rate limit
                    return page, ""
                else:
                    print(f"{Fore.YELLOW}Page {page} returned status {response.status}{Style.RESET_ALL}")
                    return page, ""
        except Exception as e:
            print(f"{Fore.RED}Error fetching page {page}: {str(e)}{Style.RESET_ALL}")
            return page, ""

def clean_card_name(name: str) -> str:
    """Clean up card name by removing suffixes and extra spaces"""
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
        print(f"{Fore.RED}Error parsing price '{price_text}': {str(e)}{Style.RESET_ALL}")
        return 0

async def process_batch(start: int, end: int, semaphore: Semaphore) -> tuple[List[Dict[str, Any]], bool]:
    """Process a batch of pages, returns (cards, should_continue)"""
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
    }
    
    scraped_data = []
    cards_seen = set()
    should_continue = True
    
    async with aiohttp.ClientSession(headers=headers) as session:
        tasks = []
        for page in range(start, end + 1):
            url = f'https://www.outland.no/samlekort-og-kortspill/magic-the-gathering/singles?p={page}&product_list_limit=100'
            tasks.append(fetch_page(session, url, page, semaphore))
        
        responses = await asyncio.gather(*tasks)
        
        for page, html in responses:
            if not html:
                continue
            
            soup = BeautifulSoup(html, 'html.parser')
            card_entries = soup.find_all('li', class_='item product product-item')
            
            if not card_entries:
                print(f"{Fore.YELLOW}No cards found on page {page}{Style.RESET_ALL}")
                should_continue = False
                break

            # Track in-stock status for this page
            total_cards = len(card_entries)
            out_of_stock_count = 0
                
            print(f"Processing page {page}: Found {total_cards} cards")

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
                    
                    card_name = clean_card_name(card_name_element.text)
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
                        # Store price in NOK (not øre)
                        price_text = price_elem.text.strip()
                        price_clean = re.sub(r'[^\d,.]', '', price_text)
                        price_clean = price_clean.replace(',', '.')
                        card_data['price'] = float(price_clean)
                    
                    if photo_link := card.find('a', class_='product-item-photo'):
                        card_data['store_url'] = photo_link.get('href', '')
                        if img := photo_link.find('img', class_='product-image-photo'):
                            card_data['image_url'] = img.get('src', '')
                    
                    if card_data['price'] > 0:
                        scraped_data.append(card_data)
                        
                except Exception as e:
                    print(f"{Fore.RED}Error processing card: {str(e)}{Style.RESET_ALL}")
                    continue

            # Make the out-of-stock detection more sensitive
            out_of_stock_ratio = out_of_stock_count / total_cards
            print(f"Page {page}: {out_of_stock_count}/{total_cards} cards out of stock ({out_of_stock_ratio:.2%})")
            
            # If we find a page that's mostly out of stock (40% or more), we're probably at the end
            if out_of_stock_ratio > 0.4:  # Lowered from 0.5 to 0.4 to be more sensitive
                print(f"{Fore.YELLOW}Stopping at page {page}: High number of out-of-stock cards ({out_of_stock_ratio:.1%}){Style.RESET_ALL}")
                should_continue = False
                break
    
    return scraped_data, should_continue

async def main():
    try:
        print(f"{Fore.BLUE}Starting scraper...{Style.RESET_ALL}")
        
        semaphore = Semaphore(5)
        batch_size = 50
        all_data = []
        current_start = 1
        
        while True:
            end = current_start + batch_size - 1
            print(f"\n{Fore.BLUE}Scraping batch {current_start}-{end}...{Style.RESET_ALL}")
            
            batch_data, should_continue = await process_batch(current_start, end, semaphore)
            all_data.extend(batch_data)
            
            save_to_file(all_data, 'scraped_cards.json')
            
            if not should_continue:
                print(f"{Fore.GREEN}Reached end of in-stock cards. Stopping.{Style.RESET_ALL}")
                break
                
            current_start = end + 1
            await asyncio.sleep(5)
        
        # Final save and display
        all_data.sort(key=lambda x: x['name'])
        save_to_file(all_data, 'scraped_cards.json')
        
        print(f"\n{Fore.BLUE}Sample of scraped cards:{Style.RESET_ALL}")
        for card in all_data[:5]:
            print(f"Name: {card['name']}")
            print(f"Price: {card['price']} NOK")
            print(f"URL: {card['store_url']}")
            print(f"Image: {card['image_url']}")
            print("-" * 50)
        
        print(f"{Fore.GREEN}Scraping completed successfully! Found {len(all_data)} cards{Style.RESET_ALL}")
        
    except Exception as e:
        print(f"{Fore.RED}Error in main scraper: {str(e)}{Style.RESET_ALL}")
        raise

def save_to_file(data: List[Dict[str, Any]], file_path: str) -> None:
    """Save scraped data to JSON file with proper formatting and metadata"""
    metadata = {
        "last_updated": datetime.now().isoformat(),
        "card_count": len(data),
        "cards": data
    }
    
    with open(file_path, 'w', encoding='utf-8') as file:
        json.dump(metadata, file, ensure_ascii=False, indent=2)
    print(f"{Fore.GREEN}Saved {len(data)} cards to {file_path}{Style.RESET_ALL}")

def run_scraper():
    asyncio.run(main())

if __name__ == "__main__":
    run_scraper()