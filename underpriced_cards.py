import json

def load_json(file_path):
    with open(file_path, 'r') as file:
        return json.load(file)

def find_underpriced_cards(scryfall_data_path="card_prices.json", outland_data_path="scraped_cards.json", threshold=2):
    scryfall_data = load_json(scryfall_data_path)
    outland_data = load_json(outland_data_path)

    underpriced_cards = []

    for outland_card in outland_data:
        card_name = outland_card['name']
        card_price_nok = outland_card['price']

        lowest_scryfall_price = float('inf')  # Set initial lowest price to infinity

        # Check if the card exists in Scryfall data and find the lowest Scryfall price
        for card in scryfall_data:
            if card['name'] == card_name:
                # Update lowest price using USD if available
                if card['prices']['usd'] and float(card['prices']['usd']) < lowest_scryfall_price:
                    lowest_scryfall_price = float(card['prices']['usd'])

                # Update lowest price using EUR if available
                if card['prices']['eur'] and float(card['prices']['eur']) * 1.05 < lowest_scryfall_price:
                    lowest_scryfall_price = float(card['prices']['eur']) * 1.05  # Convert EUR to USD
        # Convert NOK to USD using a specific conversion rate (1 NOK = 0.09 USD)
        converted_price_usd = card_price_nok * 0.09

        # Calculate the price difference in USD
        price_difference = lowest_scryfall_price - converted_price_usd

        # Check if the Outland price is significantly lower than the lowest Scryfall price
        if price_difference > threshold and price_difference != float('inf') and card_price_nok > 5:  # Adjust this threshold as needed
            underpriced_cards.append({
                'name': card_name,
                'price_difference_usd': price_difference,
                'outland_price_nok': card_price_nok,
                'lowest_scryfall_price_usd': lowest_scryfall_price,
                'store_url': outland_card['store_url']
            })

    # Sort underpriced cards based on the price difference in ascending order
    underpriced_cards.sort(key=lambda x: x['price_difference_usd'])
    
    
    # Display or further process the most underpriced cards
    for card in underpriced_cards:
        print("-" * 30)
        print(f"Name: {card['name']}")
        print(f"Outland Price (NOK): {card['outland_price_nok']}")
        print(f"Scryfall Price (USD): {card['lowest_scryfall_price_usd']}")
        print(f"Price Difference (USD): {card['price_difference_usd']}")
        print(f"Store URL: {card['store_url']}")
        print("-" * 30)


    return underpriced_cards
