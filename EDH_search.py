import json
import requests
from bs4 import BeautifulSoup
from colorama import Fore, Style
import time

class CardSearch:
    def search_outland(self, card_name, max_price):
        try:
            with open('scraped_cards.json', 'r') as file:
                scraped_cards = json.load(file)
                scraped_cards = scraped_cards['cards']
                
        except FileNotFoundError:
            print(f"{Fore.RED}Error: scraped_cards.json not found. Please run the Outland database update first.{Style.RESET_ALL}")
            return None
        except json.JSONDecodeError:
            print(f"{Fore.RED}Error: scraped_cards.json is corrupted or empty.{Style.RESET_ALL}")
            return None

        # Clean up the search name
        search_name = card_name.lower().strip()
        
        # Try exact match first
        found_cards = [card for card in scraped_cards if
                      card['name'].lower() == search_name and 
                      card['price'] <= max_price and 
                      card['price'] > 0]
        
        # If no exact match, try partial match
        if not found_cards:
            found_cards = [card for card in scraped_cards if
                          search_name in card['name'].lower() and 
                          card['price'] <= max_price and 
                          card['price'] > 0]

        if found_cards:
            # Sort by price to get the cheapest option
            found_cards.sort(key=lambda x: x['price'])
            found_card = found_cards[0]
            print(f"{Fore.GREEN}Found card: {found_card['name']} at {found_card['price']} NOK{Style.RESET_ALL}")
            return {
                'name': found_card['name'],
                'price': found_card['price'],
                'image_url': found_card.get('image_url', ''),
                'store_url': found_card['store_url'],
            }
        
        print(f"{Fore.YELLOW}No card found for: {card_name}{Style.RESET_ALL}")
        return None

    # Scrapes edh using an url and returns a list of synergistic cards
    def scrape_edh(self, url):
        print(f"\n{Fore.BLUE}Starting EDH scrape for URL: {url}{Style.RESET_ALL}")
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }

        try:
            print(f"{Fore.BLUE}Fetching page...{Style.RESET_ALL}")
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
                    print(f"{Fore.GREEN}Found {len(card_wrappers)} cards using class: {class_name}{Style.RESET_ALL}")
                    break
            
            if not card_wrappers:
                print(f"{Fore.RED}No card wrappers found. Trying alternative methods...{Style.RESET_ALL}")
                # Try finding cards by data attributes or other methods
                card_wrappers = soup.find_all(['div', 'article'], {'data-component': 'card'})
                if not card_wrappers:
                    card_wrappers = soup.find_all(['div', 'article'], {'data-card-id': True})
            
            if not card_wrappers:
                print(f"{Fore.RED}Could not find any card elements on the page{Style.RESET_ALL}")
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
                    print(f"{Fore.GREEN}Found card: {card_name}{Style.RESET_ALL}")
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
                            print(f"{Fore.BLUE}Synergy: {synergy}%{Style.RESET_ALL}")
                        except:
                            card_info['synergy_percentage'] = '0'
                    else:
                        card_info['synergy_percentage'] = '0'
                    
                    card_list.append(card_info)

            print(f"\n{Fore.GREEN}Successfully found {len(card_list)} cards{Style.RESET_ALL}")
            return card_list

        except Exception as e:
            print(f"{Fore.RED}Error during EDH scrape: {str(e)}{Style.RESET_ALL}")
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
                print("No card names found on the website using the provided structure.")
        else:
            print("Failed to retrieve data from the website.")

        return card_list
    
    