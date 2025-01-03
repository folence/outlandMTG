import EDH_search
import underpriced_cards
import scryfall_prices
import outlandMTG_database



# Scrapes outland for all card info, no need to run often.
# outlandMTG_database.run_scraper()

# Fetches card prices from scryfall and saves to a json, no need to run often.
# scryfall_prices.fetch_cards_over_one_dollar()



# Find the most underpriced cards (if there are any) on Outland.
# underpriced_cards.find_underpriced_cards()


# Scrapes edhrec for recommended cards for a commander, and searches for those cards on outland. You can change the commander url, card fetch limit and max price of the cards.#
# Uncomment the bottom part if you want to use.
searcher = EDH_search.CardSearch()
edhred_commander_url = "https://edhrec.com/commanders/agatha-of-the-vile-cauldron"
"""
commander_rec = searcher.scrape_edh(edhred_commander_url, limit=200)
for card in commander_rec:
    searcher.search_outland(card['name'], max_price=8)
"""
