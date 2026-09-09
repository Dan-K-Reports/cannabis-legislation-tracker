#!/usr/bin/env python3
"""
Cannabis Legislation Tracker - the only script you need.

    python scraper.py                 fetch from LegiScan, write bills.json + index.html
    python scraper.py --render-only   rebuild index.html from existing bills.json (no API)

This file does BOTH the fetch and the page build on purpose. Splitting them
across two scripts is what let an old copy of the page template survive and
overwrite the new one. If any other .py in this folder generates index.html,
delete it - this script warns you about them on startup.
"""

import os
import re
import sys
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

# History action text patterns that indicate a bill is dead regardless of
# what LegiScan's status code says. LegiScan misclassifies bills killed by
# sine die adjournment (e.g. "Failed pursuant to Senate Joint Resolution 1")
# as Enacted/Signed (code 6) because session-end kills register as 100%
# progression. We audit the history array to catch these.
FAILED_PATTERNS = [
    'failed',
    'defeated',
    'died',
    'withdrawn',
    'tabled',
    'indefinitely postponed',
    'pursuant to',       # catches "failed pursuant to [joint resolution]"
    'sine die',
    'adjourned sine die',
    'lost',
    'not pass',
    'did not pass',
]

def resolve_status(api_status_code, history):
    """
    Return the corrected (status_code, status_text) tuple by cross-checking
    the bill's history array against known failure patterns.

    LegiScan sometimes returns status_code=6 (Enacted/Signed) for bills that
    were killed by a sine die adjournment resolution. The history array
    contains the ground truth action text, so we scan it for failure signals
    and override to 8 (Failed/Dead) when found.

    Args:
        api_status_code: The raw integer status from the LegiScan getBill response.
        history: The list of history dicts from bill_info.get('history', []).

    Returns:
        (int, str) tuple of corrected status_code and display text.
    """
    # Only bother auditing if LegiScan claims the bill succeeded. Statuses
    # 1-4 are in-progress or passed-chamber states that don't need overriding;
    # 7 (Vetoed) and 8 (Failed) are already correct; 9 is edge-case.
    if api_status_code in (6, 5):  # Enacted or Sent to Executive
        for entry in (history or []):
            action_text = (entry.get('action') or '').lower()
            if any(pattern in action_text for pattern in FAILED_PATTERNS):
                return 8, 'Failed/Dead'

    return api_status_code, STATUS_MAP.get(api_status_code, 'Unknown')

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
                        
                        raw_status_code = bill_info.get('status', 0)
                        history = bill_info.get('history', [])
                        status_code, status_text = resolve_status(raw_status_code, history)
                        
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


BUILD_ID = '2026-09-09 register-layout'


def _warn_about_stale_generators():
    """Shout if another script in this folder also writes index.html.

    Two scripts carrying their own copy of the page template is how this
    project ended up rendering an old design over a new one.
    """
    here = os.path.dirname(os.path.abspath(__file__))
    me = os.path.basename(os.path.abspath(__file__))
    offenders = []
    for fn in sorted(os.listdir(here)):
        if not fn.endswith('.py') or fn == me:
            continue
        try:
            with open(os.path.join(here, fn), 'r', encoding='utf-8', errors='ignore') as f:
                text = f.read()
        except OSError:
            continue
        if 'bill-card' in text and 'index.html' in text:
            offenders.append(fn)
    if offenders:
        print()
        print("!" * 70)
        print("WARNING: these files also generate index.html and will overwrite")
        print("this script's output if you run them afterwards:")
        for fn in offenders:
            print("    " + fn)
        print("Delete them. This script does both the fetch and the page build.")
        print("!" * 70)
        print()

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
                Read analysis
            </a>
        '''
    else:
        analysis_btn = '''
            <span class="btn btn-disabled" title="Analysis coming soon">
                Analysis Pending
            </span>
        '''
    
    card = f'''
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
    # Collapse indentation: 689 cards of pretty-printing added ~450KB.
    return re.sub(r'\s{2,}', ' ', re.sub(r'>\s+<', '><', card)).strip()

PAGE_TEMPLATE = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Cannabis Legislation Tracker - Real-Time Bills Across All 50 States | Dan K Reports</title>
<meta name="title" content="Cannabis Legislation Tracker - Real-Time Bills Across All 50 States | Dan K Reports">
<meta name="description" content="Track cannabis legislation in real-time across all 50 states and federal government. Monitor bills, status changes, and legislative progress with data-driven BMDE analysis.">
<meta name="keywords" content="cannabis legislation, marijuana bills, cannabis policy tracker, legalization tracker, cannabis reform, state cannabis laws, federal cannabis bills, BMDE, Black Market Death Equation, cannabis market analysis">
<meta name="author" content="Daniel Kief">
<meta name="robots" content="index, follow, max-image-preview:large, max-snippet:-1, max-video-preview:-1">
<link rel="canonical" href="https://tracker.dankreports.com/">
<meta property="og:type" content="website">
<meta property="og:url" content="https://tracker.dankreports.com/">
<meta property="og:title" content="Cannabis Legislation Tracker - Real-Time Bills Across All 50 States">
<meta property="og:description" content="Track cannabis legislation in real-time across all 50 states and federal government. Monitor bills, status changes, and legislative progress with data-driven BMDE analysis.">
<meta property="og:image" content="https://tracker.dankreports.com/og-image.jpg">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta property="og:site_name" content="Dan K Reports - Cannabis Legislation Tracker">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:url" content="https://tracker.dankreports.com/">
<meta name="twitter:title" content="Cannabis Legislation Tracker - Real-Time Bills Across All 50 States">
<meta name="twitter:description" content="Track cannabis legislation in real-time across all 50 states and federal government with BMDE analysis.">
<meta name="twitter:image" content="https://tracker.dankreports.com/og-image.jpg">
<meta name="theme-color" content="#2ecc71">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
<meta name="apple-mobile-web-app-title" content="Cannabis Tracker">
<link rel="icon" type="image/png" href="logo.png">
<link rel="apple-touch-icon" href="logo.png">
<link rel="preconnect" href="https://www.dankreports.com">
<link rel="dns-prefetch" href="https://www.dankreports.com">
<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@graph": [
    {
      "@type": "WebApplication",
      "@id": "https://tracker.dankreports.com/#webapp",
      "name": "Cannabis Legislation Tracker",
      "applicationCategory": "GovernmentApplication",
      "operatingSystem": "Web Browser",
      "url": "https://tracker.dankreports.com/",
      "description": "Real-time tracking of cannabis legislation across all 50 states and federal government using LegiScan API with analysis under the Black Market Death Equation (BMDE).",
      "offers": {
        "@type": "Offer",
        "price": "0",
        "priceCurrency": "USD"
      },
      "author": {
        "@type": "Person",
        "name": "Daniel Kief"
      },
      "publisher": {
        "@type": "Organization",
        "name": "Dan K Reports",
        "url": "https://www.dankreports.com/"
      },
      "featureList": [
        "Real-time cannabis bill tracking across all 50 states",
        "Federal cannabis legislation monitoring",
        "LegiScan API integration for up-to-date data",
        "Black Market Death Equation (BMDE) analysis integration",
        "Advanced filtering by state, status, and keywords",
        "Bill status tracking and legislative progress"
      ]
    },
    {
      "@type": "WebSite",
      "@id": "https://tracker.dankreports.com/#website",
      "url": "https://tracker.dankreports.com/",
      "name": "Cannabis Legislation Tracker",
      "description": "Track cannabis legislation across America in real-time",
      "publisher": {
        "@id": "https://www.dankreports.com/#organization"
      },
      "potentialAction": {
        "@type": "SearchAction",
        "target": {
          "@type": "EntryPoint",
          "urlTemplate": "https://tracker.dankreports.com/?search={search_term_string}"
        },
        "query-input": "required name=search_term_string"
      }
    },
    {
      "@type": "Organization",
      "@id": "https://www.dankreports.com/#organization",
      "name": "Dan K Reports",
      "url": "https://www.dankreports.com/"
    },
    {
      "@type": "BreadcrumbList",
      "@id": "https://tracker.dankreports.com/#breadcrumb",
      "itemListElement": [
        {
          "@type": "ListItem",
          "position": 1,
          "name": "Home",
          "item": "https://www.dankreports.com/"
        },
        {
          "@type": "ListItem",
          "position": 2,
          "name": "Cannabis Legislation Tracker",
          "item": "https://tracker.dankreports.com/"
        }
      ]
    }
  ]
}
</script>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=IBM+Plex+Sans+Condensed:wght@400;500;600&family=Newsreader:opsz,wght@6..72,400;6..72,500;6..72,600&display=swap" rel="stylesheet">
<style>
:root{
  --paper:#edeee7;--paper-2:#e6e8de;--band:#e3e5da;
  --ink:#1e241c;--ink-soft:#5b6157;--ink-faint:#8a9083;
  --rule:#c2c7b6;--rule-strong:#9aa190;--flag:#8c2f26;
  --b1:#e3e8d2;--b2:#c0cda1;--b3:#93a76f;--b4:#5c7042;--b5:#33421f;
  --dead:#b9bcae;
  --serif:'Newsreader',Georgia,serif;
  --sans:'IBM Plex Sans Condensed','Helvetica Neue',Arial,sans-serif;
  --measure:36rem;
}
*{box-sizing:border-box;margin:0;padding:0}
html{-webkit-text-size-adjust:100%;scroll-behavior:smooth}
body{background:var(--paper);color:var(--ink);font-family:var(--serif);font-size:17px;line-height:1.6;font-variant-numeric:tabular-nums}
.sheet{max-width:66rem;margin:0 auto;padding:2rem 1.25rem 4rem}
a{color:inherit;text-decoration:underline;text-decoration-thickness:1px;text-underline-offset:2px;text-decoration-color:var(--rule-strong)}
a:hover{color:var(--flag);text-decoration-color:var(--flag)}
:focus-visible{outline:2px solid var(--flag);outline-offset:2px}

.masthead{border-bottom:3px double var(--ink);padding-bottom:1.25rem}
.issue{font-family:var(--sans);font-size:.8rem;color:var(--ink-soft);margin-bottom:1.25rem}
h1{font-family:var(--serif);font-weight:500;font-size:clamp(2rem,6vw,3.4rem);line-height:1;letter-spacing:-.015em;max-width:20ch;margin-bottom:.4rem}
.standfirst{font-size:1.05rem;color:var(--ink-soft);max-width:54ch;font-style:italic}
.colophon{margin-top:1.5rem;display:grid;grid-template-columns:repeat(auto-fit,minmax(17rem,1fr));gap:.1rem 2.5rem;font-family:var(--sans);font-size:.85rem}
.entry{display:flex;align-items:baseline;gap:.4ch;padding:.18rem 0;color:var(--ink-soft)}
.entry .lead{flex:1 1 auto;border-bottom:1px dotted var(--rule-strong);position:relative;top:-.28em;min-width:1.5rem}
.entry .val{color:var(--ink);font-weight:500;white-space:nowrap}

section{margin-top:2.75rem}
.slug{font-family:var(--sans);font-size:.78rem;font-weight:600;color:var(--flag);margin-bottom:.35rem}
h2{font-family:var(--serif);font-weight:500;font-size:1.7rem;line-height:1.15;letter-spacing:-.01em}
.note{font-family:var(--sans);font-size:.85rem;color:var(--ink-soft);max-width:56ch;margin-top:.4rem}
.rule{border:0;border-top:1px solid var(--rule);margin:.9rem 0 1.25rem}
.prose{max-width:var(--measure)}
.prose p{margin-bottom:1rem}
.prose p:last-child{margin-bottom:0}

/* ---- cartogram ---- */
.map{display:grid;grid-template-columns:repeat(11,1fr);gap:3px}
.tile{aspect-ratio:1/1;border:0;padding:0;background:var(--paper-2);font-family:var(--sans);color:var(--ink);
  display:flex;flex-direction:column;align-items:center;justify-content:center;line-height:1.05;
  box-shadow:inset 0 0 0 1px rgba(30,36,28,.10)}
.tile.blank{background:none;box-shadow:none}
.tile.has-bills{cursor:pointer}
.tile.has-bills:hover{box-shadow:inset 0 0 0 2px var(--ink)}
.tile[aria-pressed="true"]{box-shadow:inset 0 0 0 3px var(--flag)}
.tile .ab{font-size:clamp(.55rem,1.35vw,.85rem);font-weight:600}
.tile .ct{font-size:clamp(.5rem,1.1vw,.72rem);opacity:.85;display:none}
.tile.b1{background-color:var(--b1)}
.tile.b2{background-color:var(--b2)}
.tile.b3{background-color:var(--b3)}
.tile.b4{background-color:var(--b4);color:var(--paper)}
.tile.b5{background-color:var(--b5);color:var(--paper)}
.tile.enacted{border-bottom:3px solid var(--flag)}
.tile[disabled]{opacity:.35;cursor:default}
.tile[disabled]:hover{box-shadow:inset 0 0 0 1px rgba(30,36,28,.10)}
@media(min-width:640px){.tile .ct{display:block}}

.fedrow{display:flex;gap:3px;margin-bottom:3px}
.fedtile{flex:1;font-family:var(--sans);font-size:.85rem;font-weight:600;background:var(--paper-2);
  box-shadow:inset 0 0 0 1px rgba(30,36,28,.10);border:0;padding:.55rem .7rem;text-align:left;
  color:var(--ink);cursor:pointer;display:flex;justify-content:space-between;align-items:baseline}
.fedtile:hover{box-shadow:inset 0 0 0 2px var(--ink)}
.fedtile[aria-pressed="true"]{box-shadow:inset 0 0 0 3px var(--flag)}
.fedtile .ct{font-weight:500;color:var(--ink-soft)}

.legend{display:flex;flex-wrap:wrap;gap:.9rem 1.5rem;margin-top:1rem;font-family:var(--sans);font-size:.8rem;color:var(--ink-soft)}
.key{display:flex;align-items:center;gap:.45rem}
.chip{width:1.15rem;height:1.15rem;box-shadow:inset 0 0 0 1px rgba(30,36,28,.15)}
.chip.enact{background:var(--paper-2);border-bottom:3px solid var(--flag)}

/* ---- stage bar ---- */
.stagebar{display:flex;flex-direction:column;gap:1px}
.seg{display:grid;grid-template-columns:11rem 1fr 3.4rem;align-items:center;gap:.85rem;
  background:none;border:0;padding:.34rem .4rem;cursor:pointer;font-family:var(--sans);
  color:var(--ink);text-align:left;width:100%}
.seg:hover{background:var(--band)}
.seg[aria-pressed="true"]{background:var(--band);box-shadow:inset 3px 0 0 var(--flag)}
.seg[disabled]{opacity:.35;cursor:default}
.seg[disabled]:hover{background:none}
.seg-l{font-size:.86rem;font-weight:500;line-height:1.15}
.seg-track{height:14px;background:var(--paper-2);box-shadow:inset 0 0 0 1px rgba(30,36,28,.08)}
.seg-fill{display:block;height:100%;min-width:2px}
.seg-n{font-size:.92rem;font-weight:600;text-align:right}
.seg.s1 .seg-fill{background:var(--b1)}
.seg.s2 .seg-fill{background:var(--b2)}
.seg.s3 .seg-fill{background:var(--b3)}
.seg.s4 .seg-fill{background:var(--b3)}
.seg.s5 .seg-fill{background:var(--b4)}
.seg.s6 .seg-fill{background:var(--b5)}
.seg.sx .seg-fill{background:var(--dead)}
@media(max-width:560px){.seg{grid-template-columns:7.5rem 1fr 2.6rem;gap:.5rem}.seg-l{font-size:.8rem}}

/* ---- controls ---- */
.filters{margin-bottom:1rem}
.filters h3{font-family:var(--sans);font-size:.78rem;font-weight:600;color:var(--flag);margin-bottom:.5rem}
.filter-controls{display:flex;flex-wrap:wrap;gap:.7rem;align-items:center;font-family:var(--sans)}
#searchInput{flex:1 1 16rem;font-family:var(--sans);font-size:.92rem;color:var(--ink);background:var(--paper-2);
  border:1px solid var(--rule-strong);border-radius:0;padding:.42rem .6rem}
#searchInput::placeholder{color:var(--ink-faint)}
.filter-controls select{font-family:var(--sans);font-size:.9rem;color:var(--ink);background:var(--paper-2);
  border:1px solid var(--rule-strong);border-radius:0;padding:.42rem 1.7rem .42rem .55rem;appearance:none;
  background-image:linear-gradient(45deg,transparent 50%,var(--ink-soft) 50%),linear-gradient(135deg,var(--ink-soft) 50%,transparent 50%);
  background-position:calc(100% - 14px) 55%,calc(100% - 9px) 55%;background-size:5px 5px,5px 5px;background-repeat:no-repeat}
.showing{font-family:var(--sans);font-size:.85rem;color:var(--ink-soft);margin-bottom:.6rem;
  border-top:1px solid var(--ink);border-bottom:1px solid var(--rule);padding:.45rem 0}
.showing b{color:var(--ink);font-weight:600}
.clearbtn{background:none;border:0;font:inherit;color:var(--flag);cursor:pointer;text-decoration:underline;padding:0;margin-left:.6rem}

/* ---- bill register ---- */
.bills-list h2{margin-bottom:0}
#billsContainer{border-top:1px solid var(--rule)}
.bill-card{border-bottom:1px solid var(--rule);padding:.7rem 0 .7rem 0;cursor:pointer;position:relative}
.bill-card:nth-of-type(even){background:var(--band)}
.bill-card:hover{background:var(--b1)}
.bill-header{display:flex;gap:1rem;align-items:baseline;justify-content:space-between}
.bill-title{flex:1;min-width:0;padding-left:.5rem}
.bill-meta-top{font-family:var(--sans);font-size:.78rem;color:var(--ink-soft);display:flex;gap:.5rem;align-items:baseline;flex-wrap:wrap}
.state-badge{font-weight:600;color:var(--ink)}
.state-badge-federal{color:var(--flag)}
.bill-number{letter-spacing:.02em}
.bill-card h3{font-family:var(--serif);font-weight:500;font-size:1.02rem;line-height:1.3;margin-top:.1rem}
.bill-status{font-family:var(--sans);font-size:.72rem;font-weight:600;white-space:nowrap;padding:.16rem .45rem;
  background:var(--paper-2);box-shadow:inset 0 0 0 1px var(--rule-strong);margin-right:.5rem;flex-shrink:0}
.bill-card[data-status="Enacted/Signed"] .bill-status{background:var(--b5);color:var(--paper);box-shadow:none}
.bill-card[data-status="Sent to Executive"] .bill-status{background:var(--b4);color:var(--paper);box-shadow:none}
.bill-card[data-status="Passed Both Chambers"] .bill-status,
.bill-card[data-status="Passed Chamber"] .bill-status{background:var(--b3);box-shadow:none}
.bill-card[data-status="Failed/Dead"] .bill-status{background:var(--dead);color:var(--ink-soft);box-shadow:none}
.bill-description,.bill-meta,.bill-sponsors,.bill-actions{display:none}
.bill-card.open .bill-description,.bill-card.open .bill-meta,
.bill-card.open .bill-sponsors,.bill-card.open .bill-actions{display:block}
.bill-card.open{background:var(--paper-2)}
.bill-description{font-size:.95rem;color:var(--ink-soft);line-height:1.5;max-width:62ch;margin:.6rem 0 0 .5rem}
.bill-meta,.bill-sponsors{font-family:var(--sans);font-size:.82rem;color:var(--ink-soft);margin:.5rem 0 0 .5rem}
.bill-meta strong,.bill-sponsors strong{color:var(--ink);font-weight:600}
.sponsor-list{display:inline;margin-left:.3rem}
.sponsor-tag{white-space:nowrap}
.sponsor-tag:not(:last-child)::after{content:", "}
.bill-actions{margin:.7rem 0 .2rem .5rem;display:flex;gap:1.2rem;font-family:var(--sans);font-size:.85rem}
.btn-disabled{color:var(--ink-faint)}
#noResults{font-family:var(--sans);font-size:.9rem;color:var(--ink-faint);padding:2rem 0}

.notes{max-width:var(--measure);font-size:.95rem;color:var(--ink-soft);line-height:1.55}
.notes p{margin-bottom:.8rem}

footer{border-top:3px double var(--ink);margin-top:3.5rem;padding-top:1.25rem;font-family:var(--sans);font-size:.85rem;color:var(--ink-soft)}
footer .flinks{display:flex;gap:1.5rem;flex-wrap:wrap;margin-top:.6rem}

@media(prefers-reduced-motion:reduce){html{scroll-behavior:auto}}
@media print{body{background:#fff}.filters,.stagebar,.map{display:none}.bill-description{display:block}}
</style>
</head>
<body>
<div class="sheet">

<header class="masthead">
  <p class="issue">A legislative register from Dan K Reports</p>
  <h1>Cannabis Legislation Tracker</h1>
  <p class="standfirst">Every cannabis bill moving through the fifty state legislatures and Congress, with its current stage and last recorded action.</p>

  <div class="colophon">
    <div class="entry"><span>Revised</span><span class="lead"></span><span class="val">{{UPDATED}}</span></div>
    <div class="entry"><span>Bills tracked</span><span class="lead"></span><span class="val">{{TOTAL}}</span></div>
    <div class="entry"><span>Source</span><span class="lead"></span><span class="val">LegiScan</span></div>
    <div class="entry"><span>Jurisdictions</span><span class="lead"></span><span class="val">{{JURIS}}</span></div>
    <div class="entry"><span>Action dates</span><span class="lead"></span><span class="val">{{FIRST}} to {{LAST}}</span></div>
    <div class="entry"><span>Signed into law</span><span class="lead"></span><span class="val">{{ENACTED}}</span></div>
  </div>
</header>

<main>

<section id="map-section" style="margin-top:2rem">
  <p class="slug">Plate 1</p>
  <h2>Where the bills are</h2>
  <p class="note">Each square is one state, shaded by how many bills it has in play. Select a square to filter the register below. A red underline marks a state that has signed cannabis legislation into law this session.</p>
  <hr class="rule">

  <div class="fedrow">
    <button type="button" class="fedtile" data-state="US" aria-pressed="false" aria-label="Federal, {{FEDERAL}} bills">
      <span>Federal &mdash; United States Congress</span><span class="ct">{{FEDERAL}} bills</span>
    </button>
  </div>

  <div class="map" id="map" role="group" aria-label="Bill count by state">
<!--MAP-->
  </div>

  <div class="legend" aria-hidden="true">
    <span class="key"><span class="chip" style="background:var(--paper-2)"></span>none tracked</span>
    <span class="key"><span class="chip" style="background:var(--b1)"></span>1&ndash;4</span>
    <span class="key"><span class="chip" style="background:var(--b2)"></span>5&ndash;9</span>
    <span class="key"><span class="chip" style="background:var(--b3)"></span>10&ndash;19</span>
    <span class="key"><span class="chip" style="background:var(--b4)"></span>20&ndash;34</span>
    <span class="key"><span class="chip" style="background:var(--b5)"></span>35 and over</span>
    <span class="key"><span class="chip enact"></span>law enacted</span>
  </div>
</section>

<section>
  <p class="slug">Figure 1</p>
  <h2>How far they have got</h2>
  <p class="note">Most bills die in the chamber they were introduced in. Select a stage to filter the register. Counts update to match whatever state or search is already applied.</p>
  <hr class="rule">
  <div class="stagebar" id="stagebar" role="group" aria-label="Bills by legislative stage">
<!--STAGEBAR-->
  </div>
</section>

<section class="bills-list">
  <p class="slug">Register</p>
  <h2>Current cannabis bills</h2>
  <hr class="rule">

  <div class="filters">
    <h3>Filter bills</h3>
    <div class="filter-controls">
      <input type="text" id="searchInput" placeholder="Search by title, description or bill number" aria-label="Search bills">
      <select id="stateFilter" aria-label="Filter by state">
        <option value="all">All states and federal</option>
        <option value="US">Federal only</option>
      </select>
      <select id="statusFilter" aria-label="Filter by stage">
        <option value="all">All stages</option>
        <option value="Introduced">Introduced</option>
        <option value="In Committee">In Committee</option>
        <option value="Passed Chamber">Passed Chamber</option>
        <option value="Passed Both Chambers">Passed Both Chambers</option>
        <option value="Sent to Executive">Sent to Executive</option>
        <option value="Enacted/Signed">Enacted/Signed</option>
        <option value="Failed/Dead">Failed/Dead</option>
      </select>
      <select id="sortOrder" aria-label="Sort order">
        <option value="recent">Most recent action</option>
        <option value="oldest">Oldest action</option>
        <option value="stage">Furthest along</option>
        <option value="state">By state</option>
        <option value="alphabetical">By bill number</option>
      </select>
    </div>
  </div>

  <p class="showing" id="showing"></p>

  <div id="billsContainer">
<!--BILLS-->
  </div>
  <p id="noResults" hidden>No bills match these filters.</p>
</section>

<section>
  <p class="slug">Notes</p>
  <h2>Reading the register</h2>
  <hr class="rule">
  <div class="notes">
    <p>Bills are pulled from the LegiScan API and refreshed on a schedule, not continuously. The revision date in the masthead is the last time this file was rebuilt, and each bill carries the date of its own last recorded action, which may be older.</p>
    <p>Stage reflects the furthest point a bill has reached, as reported by LegiScan. A bill that has passed both chambers has not become law: it still has to be signed. Bills marked failed or dead were reported as such by the originating chamber and are kept in the register so the denominator stays honest.</p>
    <p>Select any bill to see its summary, sponsors and a link to the full text on LegiScan. In-depth analysis of significant bills is published separately at Dan K Reports, where the Black Market Death Equation is applied to policy outcomes.</p>
  </div>
</section>

</main>

<footer>
  <p>Compiled by Dan K Reports from LegiScan. Bill text and sponsor records belong to the originating legislatures.</p>
  <div class="flinks">
    <a href="https://www.dankreports.com">dankreports.com</a>
    <a href="https://prices.dankreports.com">Price tracker</a>
    <a href="https://stonks.dankreports.com">Market register</a>
  </div>
</footer>

</div>

<script>
(function(){
  'use strict';
  var container = document.getElementById('billsContainer');
  var cards = Array.prototype.slice.call(container.querySelectorAll('.bill-card'));
  var noRes = document.getElementById('noResults');
  var showing = document.getElementById('showing');
  var search = document.getElementById('searchInput');
  var stateSel = document.getElementById('stateFilter');
  var statusSel = document.getElementById('statusFilter');
  var sortSel = document.getElementById('sortOrder');
  var map = document.getElementById('map');
  var stagebar = document.getElementById('stagebar');
  var fedTile = document.querySelector('.fedtile');

  var STAGE_ORDER = {'Enacted/Signed':6,'Sent to Executive':5,'Passed Both Chambers':4,
                     'Passed Chamber':3,'In Committee':2,'Introduced':1,'Failed/Dead':0};

  // Build the state dropdown from the bills actually present.
  var states = {};
  cards.forEach(function(c){
    var s = c.dataset.state, code = c.dataset.stateCode;
    if (code !== 'US' && s) states[s] = true;
    c._text = (c.textContent || '').toLowerCase();
    c._num = (c.querySelector('.bill-number') || {}).textContent || '';
    c._stage = STAGE_ORDER[c.dataset.status] || 0;
    c.setAttribute('tabindex','0');
    c.setAttribute('role','button');
    c.setAttribute('aria-expanded','false');
  });
  var group = document.createElement('optgroup');
  group.label = 'States';
  Object.keys(states).sort().forEach(function(s){
    var o = document.createElement('option');
    o.value = s; o.textContent = s; group.appendChild(o);
  });
  stateSel.appendChild(group);

  function bandClass(n){
    if (n === 0) return 'b0';
    if (n <= 4) return 'b1';
    if (n <= 9) return 'b2';
    if (n <= 19) return 'b3';
    if (n <= 34) return 'b4';
    return 'b5';
  }

  var tiles = Array.prototype.slice.call(document.querySelectorAll('.tile.has-bills'));
  var segs = Array.prototype.slice.call(stagebar.querySelectorAll('.seg'));

  function okState(c, st){
    if (st === 'all') return true;
    if (st === 'US') return c.dataset.stateCode === 'US';
    return c.dataset.state === st;
  }
  function okStage(c, stg){ return stg === 'all' || c.dataset.status === stg; }
  function okQuery(c, q){ return !q || c._text.indexOf(q) !== -1; }

  function apply(){
    var q = search.value.trim().toLowerCase();
    var st = stateSel.value;
    var stg = statusSel.value;
    var sort = sortSel.value;

    var shown = cards.filter(function(c){ return okState(c,st) && okStage(c,stg) && okQuery(c,q); });

    shown.sort(function(a,b){
      switch(sort){
        case 'oldest': return a.dataset.date.localeCompare(b.dataset.date);
        case 'stage': return b._stage - a._stage || b.dataset.date.localeCompare(a.dataset.date);
        case 'state': return a.dataset.state.localeCompare(b.dataset.state) || b.dataset.date.localeCompare(a.dataset.date);
        case 'alphabetical': return a._num.localeCompare(b._num, undefined, {numeric:true});
        default: return b.dataset.date.localeCompare(a.dataset.date);
      }
    });

    cards.forEach(function(c){ c.hidden = true; });
    var frag = document.createDocumentFragment();
    shown.forEach(function(c){ c.hidden = false; frag.appendChild(c); });
    container.appendChild(frag);

    noRes.hidden = shown.length > 0;

    var bits = [];
    if (st !== 'all') bits.push(st === 'US' ? 'federal' : st);
    if (stg !== 'all') bits.push(stg.toLowerCase());
    if (q) bits.push('matching \u201c' + q.replace(/[<>&]/g,'') + '\u201d');
    showing.innerHTML = '<b>' + shown.length + '</b> of ' + cards.length + ' bills'
      + (bits.length ? ', ' + bits.join(', ') : '')
      + (bits.length ? '<button type="button" class="clearbtn" id="clearBtn">clear</button>' : '');

    // Facet counts: each control reports what you would actually get by
    // clicking it, given the OTHER filters already applied. Without this the
    // stage bar advertises 450 while the register returns one bill.
    var stageBase = cards.filter(function(c){ return okState(c,st) && okQuery(c,q); });
    var stageCount = {};
    stageBase.forEach(function(c){
      stageCount[c.dataset.status] = (stageCount[c.dataset.status] || 0) + 1;
    });
    var stageMax = 0;
    segs.forEach(function(s){ stageMax = Math.max(stageMax, stageCount[s.dataset.status] || 0); });
    segs.forEach(function(s){
      var n = stageCount[s.dataset.status] || 0;
      s.querySelector('.seg-n').textContent = n;
      s.querySelector('.seg-fill').style.width = (stageMax ? (n / stageMax * 100) : 0) + '%';
      s.disabled = (n === 0 && s.dataset.status !== stg);
      s.setAttribute('aria-pressed', String(s.dataset.status === stg));
      s.setAttribute('aria-label', s.dataset.status + ', ' + n + ' bills');
    });

    var stateBase = cards.filter(function(c){ return okStage(c,stg) && okQuery(c,q); });
    var stateCount = {};
    stateBase.forEach(function(c){
      stateCount[c.dataset.state] = (stateCount[c.dataset.state] || 0) + 1;
    });
    tiles.forEach(function(t){
      var n = stateCount[t.dataset.state] || 0;
      t.querySelector('.ct').textContent = n;
      t.className = t.className.replace(/\bb[0-5]\b/, bandClass(n));
      t.disabled = (n === 0 && t.dataset.state !== st);
      t.setAttribute('aria-pressed', String(t.dataset.state === st));
      t.setAttribute('aria-label', t.dataset.state + ', ' + n + ' bills');
    });
    var fedN = stateCount['US'] || 0;
    fedTile.querySelector('.ct').textContent = fedN + (fedN === 1 ? ' bill' : ' bills');
    fedTile.disabled = (fedN === 0 && st !== 'US');
    fedTile.setAttribute('aria-pressed', String(st === 'US'));
  }

  function toggle(card){
    var open = card.classList.toggle('open');
    card.setAttribute('aria-expanded', String(open));
  }

  container.addEventListener('click', function(e){
    if (e.target.closest('a')) return;
    var card = e.target.closest('.bill-card');
    if (card) toggle(card);
  });
  container.addEventListener('keydown', function(e){
    if (e.key !== 'Enter' && e.key !== ' ') return;
    var card = e.target.closest('.bill-card');
    if (card){ e.preventDefault(); toggle(card); }
  });

  function pickState(v){
    stateSel.value = (stateSel.value === v) ? 'all' : v;
    apply();
    document.querySelector('.bills-list').scrollIntoView({block:'start'});
  }
  map.addEventListener('click', function(e){
    var t = e.target.closest('.tile.has-bills');
    if (t && !t.disabled) pickState(t.dataset.state);
  });
  fedTile.addEventListener('click', function(){ pickState('US'); });

  stagebar.addEventListener('click', function(e){
    var s = e.target.closest('.seg');
    if (!s || s.disabled) return;
    statusSel.value = (statusSel.value === s.dataset.status) ? 'all' : s.dataset.status;
    apply();
    document.querySelector('.bills-list').scrollIntoView({block:'start'});
  });

  showing.addEventListener('click', function(e){
    if (e.target.id !== 'clearBtn') return;
    search.value = ''; stateSel.value = 'all'; statusSel.value = 'all';
    apply();
  });

  var t;
  search.addEventListener('input', function(){ clearTimeout(t); t = setTimeout(apply, 140); });
  [stateSel, statusSel, sortSel].forEach(function(el){ el.addEventListener('change', apply); });

  apply();
})();
</script>
</body>
</html>
"""

# Tile grid for the cartogram. None is an empty cell.
TILE_GRID = [
    ["AK", None, None, None, None, None, None, None, None, None, "ME"],
    [None, None, None, None, None, None, None, None, "VT", "NH", "MA"],
    ["WA", "ID", "MT", "ND", "MN", "WI", "MI", None, "NY", "CT", "RI"],
    ["OR", "NV", "WY", "SD", "IA", "IL", "IN", "OH", "PA", "NJ", None],
    ["CA", "UT", "CO", "NE", "MO", "KY", "WV", "VA", "MD", "DE", None],
    [None, "AZ", "NM", "KS", "AR", "TN", "NC", "SC", "DC", None, None],
    [None, None, None, "OK", "LA", "MS", "AL", "GA", None, None, None],
    ["HI", None, None, "TX", None, None, None, None, "FL", None, None],
]

TILE_NAMES = {
    "AK": "Alaska", "AL": "Alabama", "AR": "Arkansas", "AZ": "Arizona", "CA": "California",
    "CO": "Colorado", "CT": "Connecticut", "DC": "Washington DC", "DE": "Delaware",
    "FL": "Florida", "GA": "Georgia", "HI": "Hawaii", "IA": "Iowa", "ID": "Idaho",
    "IL": "Illinois", "IN": "Indiana", "KS": "Kansas", "KY": "Kentucky", "LA": "Louisiana",
    "MA": "Massachusetts", "MD": "Maryland", "ME": "Maine", "MI": "Michigan",
    "MN": "Minnesota", "MO": "Missouri", "MS": "Mississippi", "MT": "Montana",
    "NC": "North Carolina", "ND": "North Dakota", "NE": "Nebraska", "NH": "New Hampshire",
    "NJ": "New Jersey", "NM": "New Mexico", "NV": "Nevada", "NY": "New York", "OH": "Ohio",
    "OK": "Oklahoma", "OR": "Oregon", "PA": "Pennsylvania", "RI": "Rhode Island",
    "SC": "South Carolina", "SD": "South Dakota", "TN": "Tennessee", "TX": "Texas",
    "UT": "Utah", "VA": "Virginia", "VT": "Vermont", "WA": "Washington",
    "WI": "Wisconsin", "WV": "West Virginia", "WY": "Wyoming",
}

# Left-to-right progression for the stage bar. Anything not listed is treated
# as a terminal/dead stage and rendered in the muted band at the end.
STAGE_SEQUENCE = [
    ("Introduced", "s1"),
    ("In Committee", "s2"),
    ("Passed Chamber", "s3"),
    ("Passed Both Chambers", "s4"),
    ("Sent to Executive", "s5"),
    ("Enacted/Signed", "s6"),
    ("Vetoed", "sx"),
    ("Override Attempt", "sx"),
    ("Failed/Dead", "sx"),
]


def bill_count_band(n):
    """Shading band for a state tile, by number of bills in play."""
    if n == 0:
        return 0
    if n <= 4:
        return 1
    if n <= 9:
        return 2
    if n <= 19:
        return 3
    if n <= 34:
        return 4
    return 5


def build_cartogram(counts, enacted_states):
    """Render the state tile grid. counts is {state_code: bill count}."""
    tiles = []
    for row in TILE_GRID:
        for code in row:
            if not code:
                tiles.append('<div class="tile blank" aria-hidden="true"></div>')
                continue
            n = counts.get(code, 0)
            name = TILE_NAMES[code]
            cls = 'tile b%d' % bill_count_band(n)
            if code in enacted_states:
                cls += ' enacted'
            if n == 0:
                tiles.append(
                    '<div class="%s" title="%s &mdash; no bills tracked">'
                    '<span class="ab">%s</span></div>' % (cls, name, code))
            else:
                tiles.append(
                    '<button type="button" class="%s has-bills" data-state="%s" '
                    'aria-pressed="false" aria-label="%s, %d bills tracked">'
                    '<span class="ab">%s</span><span class="ct">%d</span></button>'
                    % (cls, name, name, n, code, n))
    return '\n'.join(tiles)


def build_stage_bar(stage_counts, total):
    """Render the stage bars. Bar length is relative to the largest stage so
    that a four-bill stage is still visible; JS recomputes both on filter."""
    rows = []
    biggest = max(stage_counts.values()) if stage_counts else 0
    seen = set()

    def row(stage, cls, n):
        width = (n / biggest * 100) if biggest else 0
        return ('<button type="button" class="seg %s" data-status="%s" aria-pressed="false" '
                'aria-label="%s, %d bills">'
                '<span class="seg-l">%s</span>'
                '<span class="seg-track"><span class="seg-fill" style="width:%.1f%%"></span></span>'
                '<span class="seg-n">%d</span></button>'
                % (cls, escape_html(stage), escape_html(stage), n, escape_html(stage), width, n))

    for stage, cls in STAGE_SEQUENCE:
        seen.add(stage)
        n = stage_counts.get(stage, 0)
        if n:
            rows.append(row(stage, cls, n))
    # Any status the API returns that is not in STAGE_SEQUENCE still gets a row.
    for stage, n in sorted(stage_counts.items()):
        if stage not in seen and n:
            rows.append(row(stage, 'sx', n))
    return '\n'.join(rows)


def generate_html(bills, last_updated):
    """Generate the complete index.html with every bill pre-rendered."""

    bills.sort(key=lambda x: x.get('last_action_date') or x.get('status_date') or '',
               reverse=True)

    total_bills = len(bills)
    jurisdictions = set(b['state_code'] for b in bills)

    counts = {}
    stage_counts = {}
    enacted_states = set()
    for b in bills:
        counts[b['state_code']] = counts.get(b['state_code'], 0) + 1
        stage_counts[b['status']] = stage_counts.get(b['status'], 0) + 1
        if b['status'] == 'Enacted/Signed':
            enacted_states.add(b['state_code'])

    federal_count = counts.get('US', 0)
    enacted_count = stage_counts.get('Enacted/Signed', 0)

    dates = sorted(d for d in
                   (b.get('last_action_date') or b.get('status_date') or '' for b in bills) if d)
    first_date = dates[0][:10] if dates else 'n/a'
    last_date = dates[-1][:10] if dates else 'n/a'

    last_updated_formatted = datetime.fromisoformat(
        last_updated.replace('Z', '+00:00')).strftime('%B %d, %Y at %I:%M %p')

    bill_cards_html = '\n'.join(generate_bill_card_html(b) for b in bills)

    html = (PAGE_TEMPLATE
            .replace('<!--MAP-->', build_cartogram(counts, enacted_states))
            .replace('<!--STAGEBAR-->', build_stage_bar(stage_counts, total_bills))
            .replace('<!--BILLS-->', bill_cards_html)
            .replace('{{UPDATED}}', escape_html(last_updated_formatted))
            .replace('{{TOTAL}}', str(total_bills))
            .replace('{{JURIS}}', str(len(jurisdictions)))
            .replace('{{ENACTED}}', str(enacted_count))
            .replace('{{FEDERAL}}', str(federal_count))
            .replace('{{FIRST}}', escape_html(first_date))
            .replace('{{LAST}}', escape_html(last_date)))
    return html



def main():
    render_only = '--render-only' in sys.argv or '-r' in sys.argv

    print()
    print("=" * 70)
    print("CANNABIS LEGISLATION TRACKER")
    print("build:  " + BUILD_ID)
    print("script: " + os.path.abspath(__file__))
    print("mode:   " + ("render only (no API calls)" if render_only else "fetch + build"))
    print("=" * 70)

    _warn_about_stale_generators()

    if render_only:
        if not os.path.exists('bills.json'):
            print("ERROR: bills.json not found. Run without --render-only first.")
            return 1
        with open('bills.json', 'r', encoding='utf-8') as f:
            payload = json.load(f)
        bills = payload.get('bills', [])
        last_updated = payload.get('last_updated') or datetime.now().isoformat()
        if not bills:
            print("ERROR: bills.json contains no bills. index.html left untouched.")
            return 1
        print("Loaded %d bills from bills.json" % len(bills))
    else:
        bills = fetch_all_bills()
        if not bills:
            print("ERROR: No bills returned. bills.json and index.html left untouched.")
            return 1
        last_updated = datetime.now().isoformat()
        with open('bills.json', 'w', encoding='utf-8') as f:
            json.dump({'last_updated': last_updated,
                       'total_bills': len(bills),
                       'bills': bills}, f, indent=2, ensure_ascii=False)
        print("Wrote bills.json (%d bills)" % len(bills))

    html_content = generate_html(bills, last_updated)
    with open('index.html', 'w', encoding='utf-8') as f:
        f.write(html_content)

    enacted = sum(1 for b in bills if b.get('status') == 'Enacted/Signed')
    print()
    print("=" * 70)
    print("DONE")
    print("=" * 70)
    print("Bills:         %d across %d jurisdictions"
          % (len(bills), len(set(b['state_code'] for b in bills))))
    print("Enacted/Signed: %d" % enacted)
    print("index.html:    %s bytes" % format(len(html_content), ','))
    print()
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
