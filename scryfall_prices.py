import requests
import json
from datetime import datetime

def save_cards_to_file(cards, filename='card_prices.json'):
    with open(filename, 'w') as file:
        json.dump(cards, file, indent=4)
        
def fetch_cards_over_one_dollar():
    url = 'https://api.scryfall.com/cards/search?q=usd>0.1'
    cards_over_one_dollar = []

    # Fetching data from Scryfall in pages
    has_more = True
    next_page = url

    while has_more:
        response = requests.get(next_page)
        if response.status_code == 200:
            data = response.json()
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

    # Create metadata structure
    metadata = {
        "last_updated": datetime.now().isoformat(),
        "card_count": len(cards_over_one_dollar),
        "cards": cards_over_one_dollar
    }
    
    # Save with metadata
    with open('card_prices.json', 'w') as f:
        json.dump(metadata, f, indent=2)

    return cards_over_one_dollar