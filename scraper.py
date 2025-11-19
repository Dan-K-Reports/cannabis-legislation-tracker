import requests
from bs4 import BeautifulSoup
import json
from datetime import datetime

from datetime import datetime

def scrape_bills():
    bills = []
    start_date = datetime(2025, 11, 19)  # November 19, 2025

    states = [
        {'name': 'California', 'abbr': 'CA', 'url': 'https://leginfo.legislature.ca.gov/'},
        {'name': 'Colorado', 'abbr': 'CO', 'url': 'https://leg.colorado.gov/'},
        # ... Add all 50 states with abbreviations ...
    ]

    for state in states:
        # ... Scraping logic ...

        for listing in bill_listings:
            bill_id = listing.find('span', class_='bill-id').text.strip()
            bill_number = bill_id.replace(' ', '')
            state_abbr = state['abbr']
            
            bill_date_str = listing.find('span', class_='bill-date').text.strip()
            bill_date = datetime.strptime(bill_date_str, '%m/%d/%Y')

            if bill_date >= start_date:
                silentmajority_url = f"https://www.silentmajority420.com/{state_abbr}{bill_number}"
            else:
                silentmajority_url = None

            bill = {
                # ... Other bill details ...
                'state_abbr': state_abbr,
                'number': bill_number,
                'date': bill_date_str,
                'silentmajority_url': silentmajority_url
            }
            bills.append(bill)

    # ... Save bills to JSON file ...

if __name__ == '__main__':
    scrape_bills()
