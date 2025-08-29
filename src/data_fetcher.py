#!/usr/bin/env python3
import json
import time
import argparse
import requests
import yaml
import os
from datetime import datetime
import sys

# Add current directory to Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

from filters import apply_filters

def load_config():
    """Load configuration from yaml file"""
    config_path = os.path.join(os.path.dirname(__file__), '..', 'config', 'config.yaml')
    with open(config_path, 'r') as f:
        return yaml.safe_load(f)

def fetch_coingecko_data(config):
    """Fetch comprehensive market data from CoinGecko"""
    base_url = config['coingecko']['base_url']
    rate_limit = config['coingecko']['rate_limit']
    max_pages = config['scan_pages']
    per_page = config['coins_per_page']
    
    all_coins = []
    successful_pages = 0
    
    for page in range(1, max_pages + 1):
        url = f"{base_url}/coins/markets"
        params = {
            'vs_currency': 'usd',
            'order': 'market_cap_desc',
            'per_page': per_page,
            'page': page,
            'price_change_percentage': '24h'
        }
        
        try:
            print(f"Fetching page {page}/{max_pages}...")
            response = requests.get(url, params=params, timeout=30)
            
            if response.status_code == 429:
                print(f"⚠️ Rate limit hit on page {page}. Using {successful_pages} pages of data.")
                break
            
            response.raise_for_status()
            data = response.json()
            if not data:
                break
                
            all_coins.extend(data)
            successful_pages += 1
            print(f"✅ Fetched {len(data)} coins from page {page}")
            
            if page < max_pages:
                sleep_time = rate_limit + (page * 0.2)
                time.sleep(sleep_time)
                
        except requests.RequestException as e:
            print(f"❌ Error fetching page {page}: {e}")
            if "429" in str(e):
                break
            continue
    
    print(f"📊 Successfully fetched {len(all_coins)} coins from {successful_pages} pages")
    return all_coins

def save_filtered_data(qualifying_coins):
    """Save filtered coin data to cache"""
    cache_dir = os.path.join(os.path.dirname(__file__), '..', 'cache')
    os.makedirs(cache_dir, exist_ok=True)
    
    data = {
        'timestamp': datetime.utcnow().isoformat(),
        'coins': qualifying_coins,
        'metadata': {
            'count': len(qualifying_coins),
            'last_updated': datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC'),
            'filter_criteria': 'Market Cap >= 100M + Volume >= 30M'
        }
    }
    
    cache_file = os.path.join(cache_dir, 'daily_coin_data.json')
    with open(cache_file, 'w') as f:
        json.dump(data, f, indent=2)
    
    print(f"💾 Cached {len(qualifying_coins)} qualifying coins")

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--daily-scan', action='store_true', help='Run daily market scan')
    args = parser.parse_args()
    
    if args.daily_scan:
        print("🚀 Starting daily market scan...")
        
        config = load_config()
        all_coins = fetch_coingecko_data(config)
        
        if not all_coins:
            print("❌ No coin data retrieved")
            return
        
        print(f"📈 Processing {len(all_coins)} total coins...")
        qualifying_coins = apply_filters(all_coins, config)
        save_filtered_data(qualifying_coins)
        
        print("✅ Daily scan completed successfully!")
        print(f"📊 Qualifying opportunities: {len(qualifying_coins)} coins")

if __name__ == '__main__':
    main()
