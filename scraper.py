#!/usr/bin/env python3
"""
Cannabis Legislation Tracker Scraper - All States Version
Fetches cannabis bills from all 50 states plus federal from LegiScan API.
"""

import os
import json
import requests
from datetime import datetime
import time

# LegiScan API configuration
LEGISCAN_API_KEY = os.environ.get('LEGISCAN_API_KEY')
LEGISCAN_BASE_URL = 'https://api.legiscan.com/?key={}&op={}'

# All US states plus federal
STATES = {
    'US': 'Federal',
    'AL': 'Alabama', 'AK': 'Alaska', 'AZ': 'Arizona', 'AR': 'Arkansas',
    'CA': 'California', 'CO': 'Colorado', 'CT': 'Connecticut', 'DE': 'Delaware',
    'FL': 'Florida', 'GA': 'Georgia', 'HI': 'Hawaii', 'ID': 'Idaho',
    'IL': 'Illinois', 'IN': 'Indiana', 'IA': 'Iowa', 'KS': 'Kansas',
    'KY': 'Kentucky', 'LA': 'Louisiana', 'ME': 'Maine', 'MD': 'Maryland',
    'MA': 'Massachusetts', 'MI': 'Michigan', 'MN': 'Minnesota', 'MS': 'Mississippi',
    'MO': 'Missouri', 'MT': 'Montana', 'NE': 'Nebraska', 'NV': 'Nevada',
    'NH': 'New Hampshire', 'NJ': 'New Jersey', 'NM': 'New Mexico', 'NY': 'New York',
    'NC': 'North Carolina', 'ND': 'North Dakota', 'OH': 'Ohio', 'OK': 'Oklahoma',
    'OR': 'Oregon', 'PA': 'Pennsylvania', 'RI': 'Rhode Island', 'SC': 'South Carolina',
    'SD': 'South Dakota', 'TN': 'Tennessee', 'TX': 'Texas', 'UT': 'Utah',
    'VT': 'Vermont', 'VA': 'Virginia', 'WA': 'Washington', 'WV': 'West Virginia',
    'WI': 'Wisconsin', 'WY': 'Wyoming'
}

# Policy-relevant terms to filter noise
POLICY_TERMS = [
    'bank', 'tax', 'deduction', 'commerce', 'interstate',
    'administration', 'regulation', 'decriminalization', 'scheduling',
    'tribal', 'equity', 'expungement', 'legalization', 'medical',
    'recreational', 'dispensary', 'cultivation', 'possession'
]

def is_relevant_bill(title, description):
    """Filter out non-policy bills - must be explicitly about cannabis policy"""
    
    # Combine title and description for checking
    text = (title + ' ' + description).lower()
    
    # MUST contain cannabis/marijuana (excludes immigration, general criminal justice, etc.)
    cannabis_mentioned = any(term in text for term in ['cannabis', 'marijuana', 'marihuana'])
    
    if not cannabis_mentioned:
        return False
    
    # AND must contain at least one policy term (excludes tangential mentions)
    policy_mentioned = any(term in text for term in POLICY_TERMS)
    
    return policy_mentioned
    
    # Combine title and description for checking
    text = (title + ' ' + description).lower()
    
    # Must contain at least one policy term
    return any(term in text for term in POLICY_TERMS)

def fetch_bills_for_state(state_code, state_name):
    """Fetch cannabis-related bills for a specific state"""
    
    print(f"Fetching bills for {state_name}...")
    
    # Use 2 years for all states (API limitation - doesn't support year=5)
    year_param = 2
    
    # Search for cannabis-related bills
    search_url = LEGISCAN_BASE_URL.format(LEGISCAN_API_KEY, 'getSearch')
    search_params = {
        'state': state_code,
        'query': 'cannabis OR marijuana',
        'year': year_param
    }
    
    try:
        response = requests.get(search_url, params=search_params)
        
        if response.status_code != 200:
            print(f"  Warning: Error fetching {state_name}: HTTP {response.status_code}")
            return []
        
        data = response.json()
        
        if data.get('status') != 'OK':
            print(f"  Warning: API Error for {state_name}: {data.get('alert', {}).get('message', 'Unknown')}")
            return []
        
        search_results = data.get('searchresult', {})
        
        if not search_results or search_results.get('summary', {}).get('count', 0) == 0:
            print(f"  Info: No bills found for {state_name}")
            return []
        
        bills = []
        bill_count = 0
        filtered_count = 0
        
        for bill_id, bill_data in search_results.items():
            if bill_id == 'summary':
                continue
            
            bill_count += 1
            
            # Get detailed bill information
            bill_url = LEGISCAN_BASE_URL.format(LEGISCAN_API_KEY, 'getBill')
            bill_params = {'id': bill_data.get('bill_id')}
            
            try:
                bill_response = requests.get(bill_url, params=bill_params)
                
                if bill_response.status_code == 200:
                    bill_detail = bill_response.json()
                    
                    if bill_detail.get('status') == 'OK':
                        bill_info = bill_detail.get('bill', {})
                        
                        title = bill_info.get('title', '')
                        description = bill_info.get('description', '')
                        
                        # Filter out non-relevant bills
                        if not is_relevant_bill(title, description):
                            filtered_count += 1
                            continue
                        
                        # Extract key information
                        bill = {
                            'id': bill_info.get('bill_id'),
                            'state_code': state_code,
                            'state_name': state_name,
                            'bill_number': bill_info.get('bill_number'),
                            'title': title,
                            'description': description[:500],
                            'status': bill_info.get('status_desc'),
                            'status_date': bill_info.get('status_date'),
                            'url': bill_info.get('url'),
                            'last_action': bill_info.get('last_action'),
                            'last_action_date': bill_info.get('last_action_date'),
                            'sponsors': [],
                            'analysis_url': None
                        }
                        
                        # Extract sponsors (limit to first 5)
                        for sponsor in bill_info.get('sponsors', [])[:5]:
                            bill['sponsors'].append({
                                'name': sponsor.get('name'),
                                'party': sponsor.get('party', ''),
                                'role': sponsor.get('role', '')
                            })
                        
                        bills.append(bill)
                
                # Rate limiting
                time.sleep(0.5)
                
            except Exception as e:
                print(f"  Warning: Error fetching bill details: {e}")
                continue
        
        if filtered_count > 0:
            print(f"  Info: Filtered out {filtered_count} non-policy bills")
        print(f"  Success: Found {len(bills)} relevant bills for {state_name}")
        return bills
        
    except Exception as e:
        print(f"  Warning: Error for {state_name}: {e}")
        return []

def fetch_all_bills():
    """Fetch cannabis bills from all states"""
    
    if not LEGISCAN_API_KEY:
        print("ERROR: LEGISCAN_API_KEY environment variable not set")
        return []
    
    print("=" * 70)
    print("Cannabis Legislation Tracker - Fetching All States")
    print("=" * 70)
    print()
    
    all_bills = []
    
    for state_code, state_name in STATES.items():
        bills = fetch_bills_for_state(state_code, state_name)
        all_bills.extend(bills)
        
        # Small delay between states
        time.sleep(1)
    
    return all_bills

def save_bills_data(bills):
    """Save bills data to JSON file"""
    
    # Sort bills by last action date (most recent first)
    bills.sort(key=lambda x: x.get('last_action_date') or '', reverse=True)
    
    # Group by state for statistics
    states_with_bills = set(bill['state_name'] for bill in bills)
    federal_bills = [b for b in bills if b['state_code'] == 'US']
    
    output_data = {
        'last_updated': datetime.now().isoformat(),
        'total_bills': len(bills),
        'federal_bills': len(federal_bills),
        'total_states': len(states_with_bills),
        'bills': bills
    }
    
    with open('bills.json', 'w', encoding='utf-8') as f:
        json.dump(output_data, f, indent=2, ensure_ascii=False)
    
    print()
    print("=" * 70)
    print("SUCCESS!")
    print("=" * 70)
    print(f"Total bills found: {len(bills)}")
    print(f"Federal bills: {len(federal_bills)}")
    print(f"States with bills: {len(states_with_bills)}")
    print(f"Last updated: {output_data['last_updated']}")
    print(f"Data saved to: bills.json")
    print()

def main():
    """Main function to fetch and save cannabis bills"""
    
    bills = fetch_all_bills()
    
    if bills:
        save_bills_data(bills)
        print("Next Steps:")
        print("1. Review bills.json to identify significant bills for analysis")
        print("2. Look for federal bills like SAFER Banking, MORE Act, STATES Act")
        print("3. Create analysis articles on silentmajority420.com")
        print("4. Add analysis URLs to the 'analysis_url' field in bills.json")
        print("5. Commit and push the updated bills.json to your repository")
    else:
        print("ERROR: No bills found or error occurred")

if __name__ == '__main__':
    main()
