# MTG Price Tools

A collection of Python tools for scraping and analyzing Magic: The Gathering card prices, focusing on Outland.no and EDHRec integration.

## Features

- Scrapes all MTG singles from Outland.no
- Fetches card prices from Scryfall
- Identifies underpriced cards on Outland compared to market prices
- Searches EDHRec for commander recommendations and finds those cards on Outland

## Setup

1. Install required packages:

```bash
pip install aiohttp beautifulsoup4 requests
```

2. Clone the repository and navigate to the project directory.

## Usage

### Basic Price Analysis

```python
# Scrape Outland database (run occasionally to update)
outlandMTG_database.run_scraper()

# Update Scryfall prices (run occasionally to update)
scryfall_prices.fetch_cards_over_one_dollar()

# Find underpriced cards
underpriced_cards.find_underpriced_cards()
```

### EDHRec Integration

```python
# Initialize the searcher
searcher = EDH_search.CardSearch()

# Set your commander URL
commander_url = "https://edhrec.com/commanders/agatha-of-the-vile-cauldron"

# Scrape recommendations and search Outland
commander_rec = searcher.scrape_edh(commander_url, limit=200)
for card in commander_rec:
    searcher.search_outland(card['name'], max_price=8)
```

## Files

- `outlandMTG_database.py`: Scrapes card data from Outland.no
- `scryfall_prices.py`: Fetches current market prices from Scryfall
- `underpriced_cards.py`: Compares prices to find deals
- `EDH_search.py`: Integrates with EDHRec for commander recommendations

## Tips

- Run the scrapers sparingly to avoid unnecessary server load
- Adjust the `max_price` parameter when searching for commander cards based on your budget
- The `limit` parameter in `scrape_edh()` controls how many recommended cards to fetch