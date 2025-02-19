# MTG Price Tools

A web application for finding Magic: The Gathering card deals and commander recommendations, with a focus on Norwegian retailers (Outland.no). Features EDHRec integration for commander recommendations and price comparison with international market prices.

## Features

### Commander Search
- Search for commander recommendations from EDHRec
- Filter by budget level (Any/Budget/Expensive)
- Set maximum price in NOK
- Set card limit for search results
- Shows synergy percentage from EDHRec
- Card previews on hover
- Sort by synergy, price, or name
- Direct links to purchase cards

### Price Analysis
- Scrapes all MTG singles from Outland.no
- Fetches current market prices from Scryfall
- Identifies underpriced cards by comparing local prices to international market prices
- Shows potential savings in USD
- Sort underpriced cards by savings, price, or name

### Database Management
- Automatic database updates for both Outland and Scryfall prices
- Warning indicators for outdated databases
- Status display showing last update time and card counts

## Setup

1. Install required packages:
```bash
pip install flask aiohttp beautifulsoup4 requests colorama
```

2. Clone the repository and navigate to the project directory.

3. Run the Flask application:
```bash
python app.py
```

## Usage

### Web Interface
1. Open your browser and navigate to `http://localhost:5000`
2. Use the Commander Search to find cards for your deck:
   - Paste an EDHRec commander URL
   - Select budget level (Any/Budget/Expensive)
   - Set maximum price and card limit
   - Click Search

3. Use the Underpriced Cards feature to find deals:
   - Click "Find Underpriced Cards" to see current deals
   - Sort results by savings, price, or name
   - Hover over cards to see full card images

### Database Updates
- Click "Update Outland Database" to refresh local retailer prices
- Click "Update Scryfall Prices" to refresh international market prices
- The interface will warn you if databases are more than 7 days old

## Files
- `app.py`: Flask web application
- `EDH_search.py`: EDHRec integration and card searching
- `outlandMTG_database.py`: Outland.no scraper
- `scryfall_prices.py`: Scryfall price fetcher
- `underpriced_cards.py`: Price comparison logic
- `templates/index.html`: Web interface

## Tips
- Run database updates during off-peak hours to avoid rate limiting
- The budget filter on EDHRec URLs can significantly affect card recommendations
- Card prices are converted using current exchange rates
- Hover over cards to see full card images and details