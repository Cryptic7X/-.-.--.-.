import json
import time
import argparse
import requests
import yaml
import os
from datetime import datetime
from filters import apply_filters

def load_config():
    """Load configuration from yaml file"""
    with open('config/config.yaml', 'r') as f:
        return yaml.safe_load(f)

def fetch_coingecko_data(config):
    """Fetch comprehensive market data from CoinGecko"""
    base_url = config['coingecko']['base_url']
    rate_limit = config['coingecko']['rate_limit']
    pages = config['scan_pages']
    per_page = config['coins_per_page']
    
    all_coins = []
    
    for page in range(1, pages + 1):
        url = f"{base_url}/coins/markets"
        params = {
            'vs_currency': 'usd',
            'order': 'market_cap_desc',
            'per_page': per_page,
            'page': page,
            'price_change_percentage': '24h'
        }
        
        try:
            print(f"Fetching page {page}/{pages}...")
            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            all_coins.extend(data)
            
            print(f"Fetched {len(data)} coins from page {page}")
            
            # Rate limiting
            if page < pages:
                time.sleep(rate_limit)
                
        except requests.RequestException as e:
            print(f"Error fetching page {page}: {e}")
            continue
    
    return all_coins

def save_filtered_data(standard_coins, high_risk_coins):
    """Save filtered coin data to cache"""
    os.makedirs('cache', exist_ok=True)
    
    data = {
        'timestamp': datetime.utcnow().isoformat(),
        'standard': standard_coins,
        'high_risk': high_risk_coins,
        'counts': {
            'standard': len(standard_coins),
            'high_risk': len(high_risk_coins),
            'total': len(standard_coins) + len(high_risk_coins)
        }
    }
    
    with open('cache/daily_coin_data.json', 'w') as f:
        json.dump(data, f, indent=2)
    
    print(f"Saved {len(standard_coins)} standard and {len(high_risk_coins)} high-risk coins to cache")

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--daily-scan', action='store_true', help='Run daily market scan')
    args = parser.parse_args()
    
    if args.daily_scan:
        print("Starting daily market scan...")
        
        config = load_config()
        all_coins = fetch_coingecko_data(config)
        
        print(f"Total coins fetched: {len(all_coins)}")
        
        standard_coins, high_risk_coins = apply_filters(all_coins, config)
        save_filtered_data(standard_coins, high_risk_coins)
        
        print("Daily scan completed successfully!")

if __name__ == '__main__':
    main()

