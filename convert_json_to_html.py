#!/usr/bin/env python3
"""
Quick HTML Generator - Converts existing bills.json to SSR index.html
Use this if you already have a recent bills.json file
"""

import json
from datetime import datetime

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
    status_class = get_status_class(bill.get('status', 'Unknown'))
    sponsors = bill.get('sponsors', [])[:3]
    has_more_sponsors = len(bill.get('sponsors', [])) > 3
    
    date_to_use = bill.get('last_action_date') or bill.get('status_date')
    last_action_date = format_date(date_to_use)
    
    is_federal = bill.get('state_code') == 'US'
    state_badge_class = 'state-badge-federal' if is_federal else 'state-badge-state'
    
    # Build sponsors HTML
    sponsors_html = ''
    if sponsors:
        sponsor_tags = []
        for sponsor in sponsors:
            party = f" ({escape_html(sponsor.get('party'))})" if sponsor.get('party') else ''
            sponsor_tags.append(f'<span class="sponsor-tag">{escape_html(sponsor.get("name", ""))}{party}</span>')
        
        if has_more_sponsors:
            sponsor_tags.append(f'<span class="sponsor-tag">+{len(bill.get("sponsors", [])) - 3} more</span>')
        
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
        <article class="bill-card" data-state="{escape_html(bill.get('state_name', ''))}" data-state-code="{escape_html(bill.get('state_code', ''))}" data-status="{escape_html(bill.get('status', ''))}" data-date="{escape_html(date_to_use or '')}">
            <div class="bill-header">
                <div class="bill-title">
                    <div class="bill-meta-top">
                        <span class="state-badge {state_badge_class}">{escape_html(bill.get('state_name', ''))}</span>
                        <span class="bill-number">{escape_html(bill.get('bill_number', ''))}</span>
                    </div>
                    <h3>{escape_html(bill.get('title', ''))}</h3>
                </div>
                <div class="bill-status {status_class}">
                    {escape_html(bill.get('status', 'Unknown'))}
                </div>
            </div>
            
            <p class="bill-description">
                {escape_html(bill.get('description', ''))}
            </p>
            
            <div class="bill-meta">
                <div class="bill-meta-item">
                    <strong>Last Action:</strong> {escape_html(last_action_date)}
                </div>
            </div>
            
            {sponsors_html}
            
            <div class="bill-actions">
                <a href="{escape_html(bill.get('url', '#'))}" target="_blank" rel="noopener noreferrer" class="btn btn-secondary">
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
    states_with_bills = set(bill.get('state_name', '') for bill in bills if bill.get('state_name'))
    total_states = len(states_with_bills)
    
    active_bills = [
        b for b in bills 
        if not any(term in b.get('status', '').lower() for term in ['enacted', 'vetoed', 'failed', 'dead'])
    ]
    active_count = len(active_bills)
    
    analyzed_bills = [b for b in bills if b.get('analysis_url')]
    analyzed_count = len(analyzed_bills)
    
    # Format last updated
    try:
        last_updated_formatted = datetime.fromisoformat(last_updated.replace('Z', '+00:00')).strftime('%B %d, %Y at %I:%M %p')
    except:
        last_updated_formatted = last_updated
    
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
    <title>Cannabis Legislation Tracker - Real-Time Bills Across All 50 States | Silent Majority 420</title>
    <meta name="title" content="Cannabis Legislation Tracker - Real-Time Bills Across All 50 States | Silent Majority 420">
    <meta name="description" content="Track cannabis legislation in real-time across all 50 states and federal government. Monitor bills, status changes, and legislative progress with data-driven CBDT Framework analysis.">
    <meta name="keywords" content="cannabis legislation, marijuana bills, cannabis policy tracker, legalization tracker, cannabis reform, state cannabis laws, federal cannabis bills, CBDT Framework, cannabis market analysis">
    <meta name="author" content="The Silent Majority 420">
    <meta name="robots" content="index, follow, max-image-preview:large, max-snippet:-1, max-video-preview:-1">
    <link rel="canonical" href="https://tracker.silentmajority420.com/">
    
    <!-- Open Graph / Facebook Meta Tags -->
    <meta property="og:type" content="website">
    <meta property="og:url" content="https://tracker.silentmajority420.com/">
    <meta property="og:title" content="Cannabis Legislation Tracker - Real-Time Bills Across All 50 States">
    <meta property="og:description" content="Track cannabis legislation in real-time across all 50 states and federal government. Monitor bills, status changes, and legislative progress with data-driven CBDT Framework analysis.">
    <meta property="og:image" content="https://tracker.silentmajority420.com/og-image.jpg">
    <meta property="og:image:width" content="1200">
    <meta property="og:image:height" content="630">
    <meta property="og:site_name" content="Silent Majority 420 - Cannabis Legislation Tracker">
    
    <!-- Twitter Card Meta Tags -->
    <meta name="twitter:card" content="summary_large_image">
    <meta name="twitter:url" content="https://tracker.silentmajority420.com/">
    <meta name="twitter:title" content="Cannabis Legislation Tracker - Real-Time Bills Across All 50 States">
    <meta name="twitter:description" content="Track cannabis legislation in real-time across all 50 states and federal government with CBDT Framework analysis.">
    <meta name="twitter:image" content="https://tracker.silentmajority420.com/og-image.jpg">
    
    <!-- Additional SEO Meta Tags -->
    <meta name="theme-color" content="#2ecc71">
    <meta name="apple-mobile-web-app-capable" content="yes">
    <meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
    <meta name="apple-mobile-web-app-title" content="Cannabis Tracker">
    
    <!-- Favicon -->
    <link rel="icon" type="image/png" href="logo.png">
    <link rel="apple-touch-icon" href="logo.png">
    
    <!-- Preconnect for Performance -->
    <link rel="preconnect" href="https://silentmajority420.com">
    <link rel="dns-prefetch" href="https://silentmajority420.com">
    
    <!-- Stylesheet -->
    <link rel="stylesheet" href="style.css">
    
    <!-- Structured Data / Schema.org JSON-LD -->
    <script type="application/ld+json">
    {{
      "@context": "https://schema.org",
      "@graph": [
        {{
          "@type": "WebApplication",
          "@id": "https://tracker.silentmajority420.com/#webapp",
          "name": "Cannabis Legislation Tracker",
          "applicationCategory": "GovernmentApplication",
          "operatingSystem": "Web Browser",
          "url": "https://tracker.silentmajority420.com/",
          "description": "Real-time tracking of cannabis legislation across all 50 states and federal government using LegiScan API with data-driven CBDT Framework analysis.",
          "offers": {{
            "@type": "Offer",
            "price": "0",
            "priceCurrency": "USD"
          }},
          "author": {{
            "@type": "Person",
            "name": "The Silent Majority 420",
            "identifier": "https://orcid.org/0009-0003-6779-9910",
            "url": "https://www.silentmajority420.com/author/the-silent-majority-420/"
          }},
          "publisher": {{
            "@type": "Organization",
            "name": "The Silent Majority 420 Project",
            "url": "https://www.silentmajority420.com/",
            "logo": {{
              "@type": "ImageObject",
              "url": "https://www.silentmajority420.com/content/images/size/w256h256/2025/11/output-onlinegiftools.gif"
            }}
          }},
          "featureList": [
            "Real-time cannabis bill tracking across all 50 states",
            "Federal cannabis legislation monitoring",
            "LegiScan API integration for up-to-date data",
            "CBDT Framework analysis integration",
            "Advanced filtering by state, status, and keywords",
            "Bill status tracking and legislative progress"
          ]
        }},
        {{
          "@type": "WebSite",
          "@id": "https://tracker.silentmajority420.com/#website",
          "url": "https://tracker.silentmajority420.com/",
          "name": "Cannabis Legislation Tracker",
          "description": "Track cannabis legislation across America in real-time",
          "publisher": {{
            "@id": "https://www.silentmajority420.com/#organization"
          }},
          "potentialAction": {{
            "@type": "SearchAction",
            "target": {{
              "@type": "EntryPoint",
              "urlTemplate": "https://tracker.silentmajority420.com/?search={{search_term_string}}"
            }},
            "query-input": "required name=search_term_string"
          }}
        }},
        {{
          "@type": "Organization",
          "@id": "https://www.silentmajority420.com/#organization",
          "name": "The Silent Majority 420 Project",
          "url": "https://www.silentmajority420.com/",
          "logo": {{
            "@type": "ImageObject",
            "url": "https://www.silentmajority420.com/content/images/size/w256h256/2025/11/output-onlinegiftools.gif",
            "width": 256,
            "height": 256
          }},
          "sameAs": [
            "https://www.cbdttheory.com"
          ]
        }},
        {{
          "@type": "BreadcrumbList",
          "@id": "https://tracker.silentmajority420.com/#breadcrumb",
          "itemListElement": [
            {{
              "@type": "ListItem",
              "position": 1,
              "name": "Home",
              "item": "https://www.silentmajority420.com/"
            }},
            {{
              "@type": "ListItem",
              "position": 2,
              "name": "Cannabis Legislation Tracker",
              "item": "https://tracker.silentmajority420.com/"
            }}
          ]
        }}
      ]
    }}
    </script>
</head>
<body>
    <header>
        <div class="container">
            <div class="header-content">
                <div class="header-title-row">
                    <img src="logo.png" alt="Silent Majority 420 Logo" class="header-logo">
                    <div class="header-text">
                        <h1>Cannabis Legislation Tracker</h1>
                        <p class="subtitle">All 50 States + Federal - Real-time tracking with data-driven analysis</p>
                    </div>
                </div>
            </div>
            <div class="header-meta">
                <span class="last-updated">Last Updated: <time datetime="{escape_html(last_updated)}">{escape_html(last_updated_formatted)}</time></span>
                <a href="https://silentmajority420.com" class="btn-primary" rel="noopener noreferrer">Visit Silent Majority 420</a>
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
                <a href="https://silentmajority420.com" rel="noopener noreferrer">Silent Majority 420</a> where we apply 
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
            <p>&copy; 2024 Silent Majority 420. All rights reserved.</p>
            <p>
                <a href="https://silentmajority420.com/about" rel="noopener noreferrer">About</a> | 
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
    """Main function - load bills.json and generate index.html"""
    
    print("=" * 70)
    print("Quick HTML Generator - Converting bills.json to index.html")
    print("=" * 70)
    print()
    
    # Load bills.json
    try:
        with open('bills.json', 'r', encoding='utf-8') as f:
            data = json.load(f)
    except FileNotFoundError:
        print("❌ ERROR: bills.json not found!")
        print()
        print("Make sure bills.json is in the same directory as this script.")
        return
    except json.JSONDecodeError as e:
        print(f"❌ ERROR: Invalid JSON in bills.json: {e}")
        return
    
    bills = data.get('bills', [])
    last_updated = data.get('last_updated', datetime.now().isoformat())
    
    if not bills:
        print("❌ ERROR: No bills found in bills.json")
        return
    
    print(f"✅ Loaded {len(bills)} bills from bills.json")
    print(f"   Last updated: {last_updated}")
    print()
    
    # Generate HTML
    print("🔨 Generating index.html...")
    html_content = generate_html(bills, last_updated)
    
    # Save HTML
    with open('index.html', 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    print("✅ index.html created successfully!")
    print()
    print("=" * 70)
    print("SUCCESS!")
    print("=" * 70)
    print(f"Generated index.html with {len(bills)} pre-rendered bills")
    print()
    print("✅ Google can now crawl all your bills immediately!")
    print()
    print("Next steps:")
    print("1. Test locally: python -m http.server 8000")
    print("2. View source to verify bills are pre-rendered")
    print("3. Deploy: git add . && git commit -m 'Fix SEO' && git push")
    print()

if __name__ == '__main__':
    main()
