import json
import requests
from bs4 import BeautifulSoup
from colorama import Fore, Style

class CardSearch:
    def search_outland(self, card_name, max_price):
        with open('scraped_cards.json', 'r') as file:
            scraped_cards = json.load(file)

        found_cards = [card for card in scraped_cards if
                       card_name.lower() in card['name'].lower() and card['price'] <= max_price and card['price'] > 0]

        if found_cards:
            for found_card in found_cards:
                print(Style.RESET_ALL + f"{Fore.GREEN}Name: {found_card['name']}")
                print(f"{Fore.YELLOW}Price: {found_card['price']}")
                print(f"{Fore.MAGENTA}Image URL: {found_card['image_url']}")
                print(f"{Fore.BLUE}Store Page URL: {found_card['store_url']}")
                print(Style.RESET_ALL + "-" * 30)
                return found_card


    # Scrapes edh using an url and returns a list of synergistic cards
    def scrape_edh(self, url, limit=None):
        card_list = []

        response = requests.get(url)

        if response.status_code == 200:
            soup = BeautifulSoup(response.content, 'html.parser')

            card_wrappers = soup.find_all('div', class_='Card_container__Ng56K')

            for card_wrapper in card_wrappers:
                if limit and len(card_list) >= limit:
                    break

                card_info = {}

                card_name_elem = card_wrapper.find('span', class_='Card_name__Mpa7S')
                if card_name_elem:
                    card_name = card_name_elem.text.strip()
                    card_info['name'] = card_name


                synergy_label = card_wrapper.find('div', class_='CardLabel_label__iAM7T')
                if synergy_label:
                    synergy_text = synergy_label.text.strip()
                    if '+' in synergy_text:
                        card_info['synergy_percentage'] = synergy_text.split('+')[1].split('%')[0].strip()

                if card_info:
                    card_list.append(card_info)

            if not card_list:
                print("No card information found on the website using the provided structure.")
        else:
            print("Failed to retrieve data from the website.")

        return card_list[:limit] if limit else card_list

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
    
    