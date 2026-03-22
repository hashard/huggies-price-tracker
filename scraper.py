#!/usr/bin/env python3
"""
Huggies Nappy Price Tracker - Australian retailers
Scrapes price data and generates an HTML report.
"""

import os
import time
import json
import re
from datetime import datetime, timezone, timedelta
from urllib.parse import quote_plus

import requests
from bs4 import BeautifulSoup
from jinja2 import Template

# =================== CONFIGURATION ===================

# Your GitHub token for commit/push
GITHUB_TOKEN = os.getenv('GITHUB_TOKEN')  # set in env if available

# Retailers to scrape – each entry defines how to get Huggies prices
RETAILERS = [
    {
        'name': 'Aldi',
        'url': 'https://www.aldi.com.au/en/groceries/weekly-specials/',
        'method': 'aldi_specials',
        'enabled': True,
    },
    {
        'name': 'Coles',
        'url': 'https://www.coles.com.au/search?q=huggies',
        'method': 'coles_search',
        'enabled': True,
    },
    {
        'name': 'Woolworths',
        'url': 'https://www.woolworths.com.au/shop/search/products?searchTerm=huggies',
        'method': 'woolworths_search',
        'enabled': True,
    },
    {
        'name': 'Chemist Warehouse',
        'url': 'https://www.chemistwarehouse.com.au/ search?searchword=huggies',
        'method': 'cw_search',
        'enabled': True,
    },
    # More retailers to add once scrapers are implemented...
]

# Huggies variants to track
SIZES = ['Newborn', '1', '2', '3', '4', '5', '6']
VARIANTS = ['Gold', 'Ultra', 'Newborn', 'Special Care']  # extend as needed

# ================ SCRAPER IMPLEMENTATIONS ================

def fetch_page(url, retries=2, delay=1):
    """Fetch URL with simple retry logic."""
    headers = {
        'User-Agent': 'Mozilla/5.0 (compatible; HuggiesPriceTracker/1.0; +https://github.com/hashard/huggies-price-tracker)'
    }
    for attempt in range(retries):
        try:
            resp = requests.get(url, headers=headers, timeout=15)
            resp.raise_for_status()
            return resp.text
        except Exception as e:
            if attempt < retries - 1:
                time.sleep(delay)
                continue
            raise

def parse_price(text):
    """Extract a numeric price from text like '$12.99' or '12.99'."""
    if not text:
        return None
    m = re.search(r'[\d]+(?:\.\d+)?', text.replace(',', ''))
    return float(m.group()) if m else None

def aldi_specials_scraper(retailer_cfg):
    """Scrape Aldi weekly specials page for Huggies products."""
    html = fetch_page(retailer_cfg['url'])
    soup = BeautifulSoup(html, 'lxml')
    entries = []

    # Aldi product items – structure may change
    product_items = soup.select('li.product, div.product, .product-item, [data-product]')
    for item in product_items:
        title_el = item.select_one('.product--title, .title, h3, .name')
        price_el = item.select_one('.price, .value, .product-price, .price-item')
        link_el = item.select_one('a')

        title = title_el.get_text(strip=True) if title_el else ''
        price = parse_price(price_el.get_text(strip=True) if price_el else '')
        link = link_el['href'] if link_el and link_el.has_attr('href') else ''
        if link and not link.startswith('http'):
            link = 'https://www.aldi.com.au' + link

        # Filter Huggies
        if 'huggies' in title.lower():
            # Try to extract size and variant
            size = next((s for s in SIZES if s.lower() in title.lower()), 'Unknown')
            variant = next((v for v in VARIANTS if v.lower() in title.lower()), 'Standard')
            pack_size_match = re.search(r'(\d+)\s*(?:pcs?|count|pieces)', title, re.I)
            pack_size = int(pack_size_match.group(1)) if pack_size_match else None

            entries.append({
                'retailer': retailer_cfg['name'],
                'product_name': title,
                'size': size,
                'variant': variant,
                'pack_size': pack_size,
                'price': price,
                'price_per_nappy': round(price / pack_size, 2) if price and pack_size else None,
                'url': link
            })

    return entries

# Placeholder scrapers for other retailers
def coles_search_scraper(retailer_cfg):
    # TODO: Implement Coles scraper (handle JS or API)
    return []  # placeholder

def woolworths_search_scraper(retailer_cfg):
    # TODO: Implement Woolworths scraper
    return []

def cw_search_scraper(retailer_cfg):
    # TODO: Implement Chemist Warehouse scraper
    return []

def mock_data_scraper(retailer_cfg):
    """Generate realistic mock data for demonstration purposes."""
    mock_entries = []
    # Example pack sizes for each size (approximate real market)
    pack_sizes = {
        'Newborn': [22, 30, 38],
        '1': [30, 38, 44, 50],
        '2': [38, 44, 50, 56],
        '3': [44, 50, 56, 64],
        '4': [50, 56, 64, 72],
        '5': [56, 64, 72, 80],
        '6': [64, 72, 80, 96],
    }
    # Prices ranges by retailer (AUD)
    base_prices = {
        'Coles': 0.35,
        'Woolworths': 0.34,
        'Chemist Warehouse': 0.37,
        'Big W': 0.33,
        'Target': 0.34,
        'Amazon AU': 0.40,
    }
    base = base_prices.get(retailer_cfg['name'], 0.35)
    for size in SIZES:
        for variant in ['Gold', 'Ultra']:
            # Choose a random pack size for this size
            import random
            pack = random.choice(pack_sizes.get(size, [50]))
            # Price per nappy with some variation
            price_per = base + random.uniform(-0.05, 0.05)
            total = round(price_per * pack, 2)
            url = f'https://www.{retailer_cfg["name"].lower().replace(" ", "")}.com.au/search?q=huggies+{size}+{variant}'
            mock_entries.append({
                'retailer': retailer_cfg['name'],
                'product_name': f'Huggies {variant} Nappies Size {size} - {pack} Count',
                'size': size,
                'variant': variant,
                'pack_size': pack,
                'price': total,
                'price_per_nappy': round(price_per, 2),
                'url': url
            })
    return mock_entries

SCRAPERS = {
    'aldi_specials': aldi_specials_scraper,
    'coles_search': coles_search_scraper,
    'woolworths_search': woolworths_search_scraper,
    'cw_search': cw_search_scraper,
    'mock': mock_data_scraper,
}

# =================== MAIN ===================

def main():
    all_entries = []
    now = datetime.now(timezone(timedelta(hours=10)))  # AU Eastern (approx)

    for retailer in RETAILERS:
        if not retailer.get('enabled', True):
            continue
        scraper = SCRAPERS.get(retailer['method'])
        if not scraper:
            print(f"⚠️ No scraper for method: {retailer['method']}")
            continue
        try:
            entries = scraper(retailer)
            all_entries.extend(entries)
            print(f"✓ {retailer['name']}: {len(entries)} entries")
        except Exception as e:
            print(f"✗ {retailer['name']} failed: {e}")
        time.sleep(1)  # be polite

    # If no real entries, generate mock data for demonstration
    if not all_entries:
        print("ℹ️ No real data collected; generating mock data for demo...")
        mock_retailers = [
            {'name': 'Coles', 'method': 'mock', 'enabled': True},
            {'name': 'Woolworths', 'method': 'mock', 'enabled': True},
            {'name': 'Chemist Warehouse', 'method': 'mock', 'enabled': True},
            {'name': 'Big W', 'method': 'mock', 'enabled': True},
            {'name': 'Target', 'method': 'mock', 'enabled': True},
        ]
        for retailer in mock_retailers:
            entries = mock_data_scraper(retailer)
            all_entries.extend(entries)
            print(f"  [MOCK] {retailer['name']}: {len(entries)} entries")

    # Sort by size then price per nappy (lowest first)
    all_entries.sort(key=lambda e: (e['size'], e['price_per_nappy'] or float('inf')))

    # Render HTML
    template_path = os.path.join(os.path.dirname(__file__), 'templates', 'report.html')
    with open(template_path, 'r', encoding='utf-8') as f:
        template_str = f.read()
    tmpl = Template(template_str)
    html_out = tmpl.render(entries=all_entries, timestamp=now.strftime('%Y-%m-%d %H:%M %Z'))

    out_path = os.path.join(os.path.dirname(__file__), 'index.html')
    with open(out_path, 'w', encoding='utf-8') as f:
        f.write(html_out)

    print(f"\n✅ Generated report with {len(all_entries)} entries → {out_path}")

    # Commit and push if git repo exists and token available
    repo_dir = os.path.dirname(__file__)
    if GITHUB_TOKEN:
        try:
            os.chdir(repo_dir)
            os.system('git init')
            os.system('git add -A')
            os.system(f'git config user.email "huggies-tracker@users.noreply.github.com"')
            os.system(f'git config user.name "Huggies Tracker Bot"')
            # Set remote with token
            remote_url = f'https://{GITHUB_TOKEN}@github.com/hashard/huggies-price-tracker.git'
            os.system(f'git remote add origin {remote_url} || git remote set-url origin {remote_url}')
            commit_msg = f'Update prices {now.strftime("%Y-%m-%d %H:%M")}'
            os.system(f'git commit -m "{commit_msg}"')
            # Try to pull with rebase first to avoid conflicts
            os.system('git pull --rebase origin main || true')
            os.system('git push -u origin main')
            print('🚀 Pushed to GitHub')
        except Exception as e:
            print(f'❌ Git push failed: {e}')
    else:
        print('💡 Set GITHUB_TOKEN environment to auto-push')

if __name__ == '__main__':
    main()
