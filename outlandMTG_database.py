import aiohttp
from bs4 import BeautifulSoup
import re
import asyncio
import json

async def fetch_page(session, url, page):
    if page % 25 == 0:
        print(f'Scraping page: {page}')
    async with session.get(url) as response:
        return await response.text()

async def scrape_outland_cards(start_page=1, end_page=500):
    headers = {'User-Agent': 'Your User Agent'}
    scraped_data = []
    
    async with aiohttp.ClientSession(headers=headers) as session:
        tasks = []
        for page in range(start_page, end_page + 1):
            url = f'https://www.outland.no/samlekort-og-kortspill/magic-the-gathering/singles?p={page}'
            tasks.append(fetch_page(session, url, page))
        
        responses = await asyncio.gather(*tasks)
        
        for html in responses:
            soup = BeautifulSoup(html, 'html.parser')
            card_entries = soup.find_all('li', class_='item product product-item')

            for card in card_entries:
                card_name_element = card.find('a', class_='product-item-link')
                if not card_name_element:
                    continue
                    
                card_data = {
                    'name': card_name_element.text.replace('(Enkeltkort)', '').strip(),
                    'price': 0,
                    'store_url': 'N/A'
                }
                
                if price_elem := card.find('span', class_='price'):
                    if price_digits := re.findall(r'\d+', price_elem.text):
                        card_data['price'] = int(''.join(price_digits))
                                                
                if store_elem := card.find('a', class_='product-item-photo'):
                    card_data['store_url'] = store_elem['href']
                    
                if card_data['price'] != 0:
                    scraped_data.append(card_data)
                    
    return scraped_data

def save_to_file(data, file_path):
    with open(file_path, 'w', encoding='utf-8') as file:
        json.dump(data, file, ensure_ascii=False, indent=2)

async def main():
    data = await scrape_outland_cards(1, 500)
    save_to_file(data, 'scraped_cards.json')

def run_scraper():
    asyncio.run(main())