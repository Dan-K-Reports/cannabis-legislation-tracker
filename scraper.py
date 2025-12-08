#!/usr/bin/env python3
"""
Cannabis Legislation Tracker Scraper - SSR (Server-Side Rendering) Version
Generates a complete index.html with all bills pre-rendered for SEO.
"""

import os
import json
import requests
from datetime import datetime
import time

# LegiScan API configuration
LEGISCAN_API_KEY = os.environ.get('LEGISCAN_API_KEY')
LEGISCAN_BASE_URL = 'https://api.legiscan.com/?key={}&op={}'

# LegiScan status code mapping
STATUS_MAP = {
    1: 'Introduced',
    2: 'In Committee',
    3: 'Passed Chamber',
    4: 'Passed Both Chambers',
    5: 'Sent to Executive',
    6: 'Enacted/Signed',
    7: 'Vetoed',
    8: 'Failed/Dead',
    9: 'Override Attempt'
}

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
    'bank', 'banking', 'tax', 'deduction', '280e', 'safe banking',
    'commerce', 'interstate', 'import', 'export', 'trade',
    'administration', 'regulation', 'regulatory', 'rule', 'rulemaking',
    'license', 'licensing', 'licensee', 'permit',
    'scheduling', 'schedule i', 'schedule ii', 'schedule iii',
    'decriminalization', 'legalization', 'legalize',
    'medical', 'recreational', 'adult-use', 'adult use',
    'dispensary', 'dispensaries', 'cultivation', 'cultivator',
    'manufacturer', 'manufacturing', 'processor', 'retailer',
    'delivery', 'transporter',
    'enforcement', 'compliance', 'violation', 'penalty', 'penalties',
    'black market', 'gray market', 'grey market', 'illicit',
    'testing', 'test', 'potency', 'thc', 'cbd', 'contaminant',
    'pesticide', 'lab', 'laboratory',
    'equity', 'social equity', 'expungement', 'record', 'conviction',
    'tribal', 'reservation',
    'fund', 'funding', 'grant', 'appropriation', 'cash fund',
    'revenue', 'fee', 'fees',
    'possession', 'consume', 'consumption', 'use', 'impairment',
    'dui', 'dwi', 'workplace',
    'hemp', 'research', 'study', 'pilot', 'program'
]

def is_relevant_bill(title, description):
    """Filter out non-policy bills"""
    text = (title + ' ' + description).lower()
    cannabis_mentioned = any(term in text for term in ['cannabis', 'marijuana', 'marihuana'])
    
    if not cannabis_mentioned:
        return False
    
    policy_mentioned = any(term in text for term in POLICY_TERMS)
    return policy_mentioned

def fetch_bills_for_state(state_code, state_name):
    """Fetch cannabis-related bills for a specific state"""
    print(f"Fetching bills for {state_name}...")
    
    year_param = 2
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
        filtered_count = 0
        
        for bill_id, bill_data in search_results.items():
            if bill_id == 'summary':
                continue
            
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
                        
                        if not is_relevant_bill(title, description):
                            filtered_count += 1
                            continue
                        
                        status_code = bill_info.get('status', 0)
                        status_text = STATUS_MAP.get(status_code, 'Unknown')
                        
                        bill = {
                            'id': bill_info.get('bill_id'),
                            'state_code': state_code,
                            'state_name': state_name,
                            'bill_number': bill_info.get('bill_number'),
                            'title': title,
                            'description': description[:500],
                            'status': status_text,
                            'status_code': status_code,
                            'status_date': bill_info.get('status_date'),
                            'url': bill_info.get('url'),
                            'last_action': bill_info.get('last_action'),
                            'last_action_date': bill_info.get('last_action_date'),
                            'sponsors': [],
                            'analysis_url': None
                        }
                        
                        for sponsor in bill_info.get('sponsors', [])[:5]:
                            bill['sponsors'].append({
                                'name': sponsor.get('name'),
                                'party': sponsor.get('party', ''),
                                'role': sponsor.get('role', '')
                            })
                        
                        bills.append(bill)
                
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
        time.sleep(1)
    
    return all_bills

def escape_html(text):
    """Escape HTML special characters"""
    if not text:
        return ''
    return (str(text)
            .replace('&', '&amp;')
            .replace('<', '&lt;')
            .replace('>', '&gt;')
            .replace('"', '&quot;')
            .replace("'", '&#39;'))

def get_status_class(status):
    """Get CSS class for bill status"""
    status_lower = status.lower()
    
    if 'introduced' in status_lower:
        return 'status-introduced'
    if 'committee' in status_lower:
        return 'status-committee'
    if 'passed' in status_lower:
        return 'status-passed'
    if 'enacted' in status_lower or 'signed' in status_lower:
        return 'status-enacted'
    
    return 'status-introduced'

def format_date(date_str):
    """Format date string"""
    if not date_str:
        return 'Unknown'
    
    try:
        date = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
        return date.strftime('%b %d, %Y')
    except:
        return date_str

def generate_bill_card_html(bill):
    """Generate HTML for a single bill card"""
    status_class = get_status_class(bill['status'])
    sponsors = bill['sponsors'][:3]
    has_more_sponsors = len(bill['sponsors']) > 3
    
    date_to_use = bill.get('last_action_date') or bill.get('status_date')
    last_action_date = format_date(date_to_use)
    
    is_federal = bill['state_code'] == 'US'
    state_badge_class = 'state-badge-federal' if is_federal else 'state-badge-state'
    
    # Build sponsors HTML
    sponsors_html = ''
    if sponsors:
        sponsor_tags = []
        for sponsor in sponsors:
            party = f" ({escape_html(sponsor.get('party'))})" if sponsor.get('party') else ''
            sponsor_tags.append(f'<span class="sponsor-tag">{escape_html(sponsor["name"])}{party}</span>')
        
        if has_more_sponsors:
            sponsor_tags.append(f'<span class="sponsor-tag">+{len(bill["sponsors"]) - 3} more</span>')
        
        sponsors_html = f'''
            <div class="bill-sponsors">
                <strong>Sponsors:</strong>
                <div class="sponsor-list">
                    {' '.join(sponsor_tags)}
                </div>
            </div>
        '''
    
    # Build analysis button HTML
    if bill.get('analysis_url'):
        analysis_btn = f'''
            <a href="{escape_html(bill['analysis_url'])}" target="_blank" rel="noopener noreferrer" class="btn btn-analysis">
                Read CBDT Analysis
            </a>
        '''
    else:
        analysis_btn = '''
            <span class="btn btn-disabled" title="Analysis coming soon">
                Analysis Pending
            </span>
        '''
    
    return f'''
        <article class="bill-card" data-state="{escape_html(bill['state_name'])}" data-state-code="{escape_html(bill['state_code'])}" data-status="{escape_html(bill['status'])}" data-date="{escape_html(date_to_use or '')}">
            <div class="bill-header">
                <div class="bill-title">
                    <div class="bill-meta-top">
                        <span class="state-badge {state_badge_class}">{escape_html(bill['state_name'])}</span>
                        <span class="bill-number">{escape_html(bill['bill_number'])}</span>
                    </div>
                    <h3>{escape_html(bill['title'])}</h3>
                </div>
                <div class="bill-status {status_class}">
                    {escape_html(bill['status'])}
                </div>
            </div>
            
            <p class="bill-description">
                {escape_html(bill['description'])}
            </p>
            
            <div class="bill-meta">
                <div class="bill-meta-item">
                    <strong>Last Action:</strong> {escape_html(last_action_date)}
                </div>
            </div>
            
            {sponsors_html}
            
            <div class="bill-actions">
                <a href="{escape_html(bill['url'])}" target="_blank" rel="noopener noreferrer" class="btn btn-secondary">
                    View on LegiScan
                </a>
                {analysis_btn}
            </div>
        </article>
    '''

def generate_html(bills, last_updated):
    """Generate complete HTML file with pre-rendered bills"""
    
    # Sort bills by most recent first
    bills.sort(key=lambda x: x.get('last_action_date') or x.get('status_date') or '', reverse=True)
    
    # Calculate stats
    total_bills = len(bills)
    states_with_bills = set(bill['state_name'] for bill in bills)
    total_states = len(states_with_bills)
    
    active_bills = [
        b for b in bills 
        if not any(term in b['status'].lower() for term in ['enacted', 'vetoed', 'failed', 'dead'])
    ]
    active_count = len(active_bills)
    
    analyzed_bills = [b for b in bills if b.get('analysis_url')]
    analyzed_count = len(analyzed_bills)
    
    # Format last updated
    last_updated_formatted = datetime.fromisoformat(last_updated.replace('Z', '+00:00')).strftime('%B %d, %Y at %I:%M %p')
    
    # Generate bill cards HTML
    bill_cards_html = '\n'.join(generate_bill_card_html(bill) for bill in bills)
    
    # Generate state options for filter
    sorted_states = sorted([s for s in states_with_bills if s != 'Federal'])
    state_options_html = '\n'.join(
        f'<option value="{escape_html(state)}">{escape_html(state)}</option>'
        for state in sorted_states
    )
    
    html = f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    
    <!-- Primary Meta Tags -->
    <title>Cannabis Legislation Tracker - Real-Time Bills Across All 50 States | Dan K Reports</title>
    <meta name="title" content="Cannabis Legislation Tracker - Real-Time Bills Across All 50 States | Dan K Reports">
    <meta name="description" content="Track cannabis legislation in real-time across all 50 states and federal government. Monitor bills, status changes, and legislative progress with data-driven CBDT Framework analysis.">
    <meta name="keywords" content="cannabis legislation, marijuana bills, cannabis policy tracker, legalization tracker, cannabis reform, state cannabis laws, federal cannabis bills, CBDT Framework, cannabis market analysis">
    <meta name="author" content="Daniel Kief">
    <meta name="robots" content="index, follow, max-image-preview:large, max-snippet:-1, max-video-preview:-1">
    <link rel="canonical" href="https://tracker.dankreports.com/">
    
    <!-- Open Graph / Facebook Meta Tags -->
    <meta property="og:type" content="website">
    <meta property="og:url" content="https://tracker.dankreports.com/">
    <meta property="og:title" content="Cannabis Legislation Tracker - Real-Time Bills Across All 50 States">
    <meta property="og:description" content="Track cannabis legislation in real-time across all 50 states and federal government. Monitor bills, status changes, and legislative progress with data-driven CBDT Framework analysis.">
    <meta property="og:image" content="https://tracker.dankreports.com/og-image.jpg">
    <meta property="og:image:width" content="1200">
    <meta property="og:image:height" content="630">
    <meta property="og:site_name" content="Dan K Reports - Cannabis Legislation Tracker">
    
    <!-- Twitter Card Meta Tags -->
    <meta name="twitter:card" content="summary_large_image">
    <meta name="twitter:url" content="https://tracker.dankreports.com/">
    <meta name="twitter:title" content="Cannabis Legislation Tracker - Real-Time Bills Across All 50 States">
    <meta name="twitter:description" content="Track cannabis legislation in real-time across all 50 states and federal government with CBDT Framework analysis.">
    <meta name="twitter:image" content="https://tracker.dankreports.com/og-image.jpg">
    
    <!-- Additional SEO Meta Tags -->
    <meta name="theme-color" content="#2ecc71">
    <meta name="apple-mobile-web-app-capable" content="yes">
    <meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
    <meta name="apple-mobile-web-app-title" content="Cannabis Tracker">
    
    <!-- Favicon -->
    <link rel="icon" type="image/png" href="logo.png">
    <link rel="apple-touch-icon" href="logo.png">
    
    <!-- Preconnect for Performance -->
    <link rel="preconnect" href="https://dankreports.com">
    <link rel="dns-prefetch" href="https://dankreports.com">
    
    <!-- Stylesheet -->
    <link rel="stylesheet" href="style.css">
    
    <!-- Structured Data / Schema.org JSON-LD -->
    <script type="application/ld+json">
    {{{{
      "@context": "https://schema.org",
      "@graph": [
        {{{{
          "@type": "WebApplication",
          "@id": "https://tracker.dankreports.com/#webapp",
          "name": "Cannabis Legislation Tracker",
          "applicationCategory": "GovernmentApplication",
          "operatingSystem": "Web Browser",
          "url": "https://tracker.dankreports.com/",
          "description": "Real-time tracking of cannabis legislation across all 50 states and federal government using LegiScan API with data-driven CBDT Framework analysis.",
          "offers": {{{{
            "@type": "Offer",
            "price": "0",
            "priceCurrency": "USD"
          }}}},
          "author": {{{{
            "@type": "Person",
            "name": "Daniel Kief",
            "url": "https://www.dankreports.com/"
          }}}},
          "publisher": {{{{
            "@type": "Organization",
            "name": "Dan K Reports",
            "url": "https://www.dankreports.com/",
            "logo": {{{{
              "@type": "ImageObject",
              "url": "https://www.dankreports.com/content/images/size/w256h256/2025/11/output-onlinegiftools.gif"
            }}}}
          }}}},
          "featureList": [
            "Real-time cannabis bill tracking across all 50 states",
            "Federal cannabis legislation monitoring",
            "LegiScan API integration for up-to-date data",
            "CBDT Framework analysis integration",
            "Advanced filtering by state, status, and keywords",
            "Bill status tracking and legislative progress"
          ]
        }}}},
        {{{{
          "@type": "WebSite",
          "@id": "https://tracker.dankreports.com/#website",
          "url": "https://tracker.dankreports.com/",
          "name": "Cannabis Legislation Tracker",
          "description": "Track cannabis legislation across America in real-time",
          "publisher": {{{{
            "@id": "https://www.dankreports.com/#organization"
          }}}},
          "potentialAction": {{{{
            "@type": "SearchAction",
            "target": {{{{
              "@type": "EntryPoint",
              "urlTemplate": "https://tracker.dankreports.com/?search={{{{search_term_string}}}}"
            }}}},
            "query-input": "required name=search_term_string"
          }}}}
        }}}},
        {{{{
          "@type": "Organization",
          "@id": "https://www.dankreports.com/#organization",
          "name": "Dan K Reports",
          "url": "https://www.dankreports.com/",
          "logo": {{{{
            "@type": "ImageObject",
            "url": "https://www.dankreports.com/content/images/size/w256h256/2025/11/output-onlinegiftools.gif",
            "width": 256,
            "height": 256
          }}}},
          "sameAs": [
            "https://www.cbdttheory.com"
          ]
        }}}},
        {{{{
          "@type": "BreadcrumbList",
          "@id": "https://tracker.dankreports.com/#breadcrumb",
          "itemListElement": [
            {{{{
              "@type": "ListItem",
              "position": 1,
              "name": "Home",
              "item": "https://www.dankreports.com/"
            }}}},
            {{{{
              "@type": "ListItem",
              "position": 2,
              "name": "Cannabis Legislation Tracker",
              "item": "https://tracker.dankreports.com/"
            }}}}
          ]
        }}}}
      ]
    }}}}
    </script>
</head>
<body>
    <header>
        <div class="container">
            <div class="header-content">
                <div class="header-title-row">
                    <img src="logo.png" alt="Dan K Reports Logo" class="header-logo">
                    <div class="header-text">
                        <h1>Cannabis Legislation Tracker</h1>
                        <p class="subtitle">All 50 States + Federal - Real-time tracking with data-driven analysis</p>
                    </div>
                </div>
            </div>
            <div class="header-meta">
                <span class="last-updated">Last Updated: <time datetime="{escape_html(last_updated)}">{escape_html(last_updated_formatted)}</time></span>
                <a href="https://dankreports.com" class="btn-primary" rel="noopener noreferrer">Visit Dan K Reports</a>
            </div>
        </div>
    </header>

    <main class="container">
        <section class="intro">
            <h2>Track Cannabis Policy Across America</h2>
            <p>
                This tracker monitors cannabis legislation across all 50 states and the federal government using the LegiScan API, 
                providing up-to-date information on bills, status changes, and legislative progress. 
                For in-depth analysis of significant bills, visit 
                <a href="https://dankreports.com" rel="noopener noreferrer">Dan K Reports</a> where we apply 
                the Consumer-Driven Black Market Displacement (CBDT) Framework to predict policy outcomes.
            </p>
        </section>

        <section class="filters">
            <h3>Filter Bills</h3>
            <div class="filter-controls">
                <input type="text" id="searchInput" placeholder="Search bills by title, description, or bill number..." aria-label="Search bills">
                
                <select id="stateFilter" aria-label="Filter by state">
                    <option value="all">All States + Federal</option>
                    <option value="US">Federal Only</option>
                    <optgroup label="States">
                        {state_options_html}
                    </optgroup>
                </select>

                <select id="statusFilter" aria-label="Filter by status">
                    <option value="all">All Statuses</option>
                    <option value="introduced">Introduced</option>
                    <option value="committee">In Committee</option>
                    <option value="passed">Passed</option>
                    <option value="enacted">Enacted</option>
                </select>

                <select id="sortOrder" aria-label="Sort order">
                    <option value="recent">Most Recent</option>
                    <option value="oldest">Oldest First</option>
                    <option value="state">By State</option>
                    <option value="alphabetical">By Bill Number</option>
                </select>
            </div>
        </section>

        <section class="stats">
            <div class="stat-card">
                <h4>Total Bills</h4>
                <p class="stat-number">{total_bills}</p>
            </div>
            <div class="stat-card">
                <h4>States Tracked</h4>
                <p class="stat-number">{total_states}</p>
            </div>
            <div class="stat-card">
                <h4>Active Bills</h4>
                <p class="stat-number">{active_count}</p>
            </div>
            <div class="stat-card">
                <h4>With Analysis</h4>
                <p class="stat-number">{analyzed_count}</p>
            </div>
        </section>

        <section class="bills-list">
            <h2>Current Cannabis Bills</h2>
            <div id="billsContainer">
                {bill_cards_html}
            </div>
            <div id="noResults" class="no-results" style="display: none;">
                <p>No bills found matching your criteria.</p>
            </div>
        </section>
    </main>

    <footer>
        <div class="container">
            <p>&copy; 2025 Dan K Reports. All rights reserved.</p>
            <p>
                <a href="https://dankreports.com/about" rel="noopener noreferrer">About</a> | 
                <a href="https://www.cbdttheory.com" rel="noopener noreferrer">CBDT Framework</a> | 
                <a href="/sitemap.xml">Sitemap</a>
            </p>
        </div>
    </footer>

    <script src="app.js"></script>
</body>
</html>
'''
    
    return html

def main():
    """Main function"""
    
    # Fetch bills
    bills = fetch_all_bills()
    
    if not bills:
        print("ERROR: No bills found")
        return
    
    # Get timestamp
    last_updated = datetime.now().isoformat()
    
    # Save JSON (for reference/backup)
    with open('bills.json', 'w', encoding='utf-8') as f:
        json.dump({
            'last_updated': last_updated,
            'total_bills': len(bills),
            'bills': bills
        }, f, indent=2, ensure_ascii=False)
    
    # Generate HTML
    html_content = generate_html(bills, last_updated)
    
    # Save HTML
    with open('index.html', 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    print()
    print("=" * 70)
    print("SUCCESS!")
    print("=" * 70)
    print(f"Total bills: {len(bills)}")
    print(f"Files generated:")
    print("  - bills.json (data backup)")
    print("  - index.html (SEO-optimized with pre-rendered content)")
    print()
    print(f"✅ Google can now crawl all {len(bills)} bills immediately!")
    print()

if __name__ == '__main__':
    main()
