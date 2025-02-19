from flask import Flask, render_template, request, jsonify
import EDH_search
import underpriced_cards
import scryfall_prices
import outlandMTG_database
import asyncio
import json
from datetime import datetime

app = Flask(__name__)

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/search_commander', methods=['POST'])
def search_commander():
    try:
        data = request.json
        commander_url = data.get('commander_url')
        max_price = float(data.get('max_price', 8))
        limit = int(data.get('limit', 25))

        print(f"Searching for commander cards from: {commander_url}")
        print(f"Max price: {max_price} NOK, Limit: {limit} cards")

        searcher = EDH_search.CardSearch()
        commander_rec = searcher.scrape_edh(commander_url)
        
        print(f"Found {len(commander_rec)} recommended cards")
        
        results = []
        for card in commander_rec:
            if len(results) >= limit:
                break
                
            found_card = searcher.search_outland(card['name'], max_price=max_price)
            if found_card:
                found_card['synergy'] = card.get('synergy_percentage', '0')
                results.append(found_card)
        
        print(f"Found {len(results)} matching cards on Outland")
        return jsonify(results)
    
    except Exception as e:
        print(f"Error in search_commander: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/underpriced', methods=['GET'])
def get_underpriced():
    results = underpriced_cards.find_underpriced_cards()
    return jsonify(results)

@app.route('/update_database', methods=['POST'])
def update_database():
    try:
        data_type = request.json.get('type', '').lower()  # Convert to lowercase
        if data_type == 'outland':
            outlandMTG_database.run_scraper()
            message = "Outland database updated successfully"
        elif data_type == 'scryfall':
            scryfall_prices.fetch_cards_over_one_dollar()
            message = "Scryfall prices updated successfully"
        else:
            return jsonify({'error': f'Invalid update type: {data_type}'}), 400
        
        return jsonify({'message': message})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/database_status')
def database_status():
    try:
        outland_data = {}
        scryfall_data = []
        
        try:
            with open('scraped_cards.json', 'r', encoding='utf-8') as f:
                outland_data = json.load(f)
        except FileNotFoundError:
            outland_data = {"last_updated": None, "card_count": 0}
            
        try:
            with open('card_prices.json', 'r') as f:
                scryfall_data = json.load(f)
        except FileNotFoundError:
            scryfall_data = []
            
        # Return properly structured response
        response = {
            'outland': {
                'last_updated': outland_data.get('last_updated'),
                'card_count': outland_data.get('card_count', len(outland_data.get('cards', [])))
            },
            'scryfall': {
                'last_updated': scryfall_data.get('last_updated'), 
                'card_count': scryfall_data.get('card_count')
            }
        }
        return jsonify(response)
    except Exception as e:
        print(f"Database status error: {str(e)}")
        return jsonify({
            'outland': {'last_updated': None, 'card_count': 0},
            'scryfall': {'last_updated': None, 'card_count': 0}
        })

if __name__ == '__main__':
    app.run(debug=True) 