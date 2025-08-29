#!/usr/bin/env python3
"""
Professional CipherB 4H System - Market Data Fetcher
Handles CoinGecko API interactions with professional error handling
"""

import json
import time
import argparse
import requests
import yaml
import os
from datetime import datetime
import sys

current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

from filters import apply_professional_filters

class ProfessionalDataFetcher:
    def __init__(self, config_path='config/config.yaml'):
        self.config = self.load_configuration(config_path)
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'CipherB-Professional-System/2.0',
            'Accept': 'application/json'
        })
    
    def load_configuration(self, config_path):
        """Load system configuration"""
        full_path = os.path.join(os.path.dirname(__file__), '..', config_path)
        with open(full_path, 'r') as f:
            return yaml.safe_load(f)
    
    def fetch_comprehensive_market_data(self):
        """Fetch market data with professional error handling and retry logic"""
        base_url = self.config['coingecko']['base_url']
        rate_limit = self.config['coingecko']['rate_limit']
        timeout = self.config['coingecko']['timeout']
        pages = self.config['scan']['pages']
        per_page = self.config['scan']['coins_per_page']
        
        all_coins = []
        successful_pages = 0
        
        print(f"🚀 Starting professional market scan...")
        print(f"📊 Target: {pages} pages × {per_page} coins = {pages * per_page} coins")
        
        for page in range(1, pages + 1):
            url = f"{base_url}/coins/markets"
            params = {
                'vs_currency': 'usd',
                'order': 'market_cap_desc',
                'per_page': per_page,
                'page': page,
                'price_change_percentage': '24h',
                'sparkline': 'false'
            }
            
            retry_count = 0
            max_retries = 3
            
            while retry_count < max_retries:
                try:
                    print(f"📥 Fetching page {page}/{pages} (attempt {retry_count + 1})")
                    
                    response = self.session.get(url, params=params, timeout=timeout)
                    
                    if response.status_code == 429:
                        wait_time = rate_limit * (2 ** retry_count)
                        print(f"⚠️ Rate limit hit. Waiting {wait_time}s...")
                        time.sleep(wait_time)
                        retry_count += 1
                        continue
                    
                    response.raise_for_status()
                    data = response.json()
                    
                    if not data:
                        print(f"⚠️ Empty response from page {page}")
                        break
                    
                    all_coins.extend(data)
                    successful_pages += 1
                    print(f"✅ Page {page}: {len(data)} coins retrieved")
                    break
                    
                except requests.RequestException as e:
                    retry_count += 1
                    if retry_count >= max_retries:
                        print(f"❌ Failed to fetch page {page} after {max_retries} attempts: {e}")
                        if "429" in str(e) or "rate" in str(e).lower():
                            print("⚠️ Rate limit exceeded. Continuing with available data.")
                            break
                    else:
                        wait_time = rate_limit * retry_count
                        time.sleep(wait_time)
            
            # Rate limiting between successful pages
            if page < pages and successful_pages == page:
                sleep_time = rate_limit + (page * 0.1)
                print(f"⏳ Rate limiting: {sleep_time:.1f}s...")
                time.sleep(sleep_time)
        
        print(f"📊 Market scan complete: {len(all_coins)} coins from {successful_pages} pages")
        return all_coins, successful_pages
    
    def save_professional_cache(self, qualifying_coins, metadata):
        """Save market data with professional metadata"""
        cache_dir = os.path.join(os.path.dirname(__file__), '..', 'cache')
        os.makedirs(cache_dir, exist_ok=True)
        
        cache_data = {
            'system': {
                'name': self.config['system']['name'],
                'version': self.config['system']['version'],
                'timeframe': self.config['system']['timeframe']
            },
            'timestamp': datetime.utcnow().isoformat(),
            'coins': qualifying_coins,
            'metadata': {
                'total_coins': len(qualifying_coins),
                'filter_criteria': self.config['market_filter'],
                'last_updated': datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC'),
                'scan_performance': metadata
            }
        }
        
        cache_file = os.path.join(cache_dir, 'professional_market_data.json')
        with open(cache_file, 'w') as f:
            json.dump(cache_data, f, indent=2)
        
        print(f"💾 Professional cache saved: {len(qualifying_coins)} coins")
        return cache_file

def main():
    parser = argparse.ArgumentParser(description='Professional CipherB Market Data Fetcher')
    parser.add_argument('--daily-scan', action='store_true', help='Run daily market scan')
    args = parser.parse_args()
    
    if args.daily_scan:
        fetcher = ProfessionalDataFetcher()
        
        # Fetch comprehensive market data
        all_coins, pages_fetched = fetcher.fetch_comprehensive_market_data()
        
        if not all_coins:
            print("❌ No market data retrieved")
            return
        
        # Apply professional filters
        qualifying_coins = apply_professional_filters(all_coins, fetcher.config)
        
        # Save with metadata
        metadata = {
            'pages_fetched': pages_fetched,
            'total_raw_coins': len(all_coins),
            'qualifying_coins': len(qualifying_coins),
            'filter_efficiency': f"{len(qualifying_coins)/len(all_coins)*100:.1f}%"
        }
        
        cache_file = fetcher.save_professional_cache(qualifying_coins, metadata)
        
        print("\n" + "="*60)
        print("🎯 PROFESSIONAL MARKET SCAN COMPLETE")
        print("="*60)
        print(f"📊 Raw coins scanned: {len(all_coins)}")
        print(f"✅ Qualifying coins: {len(qualifying_coins)}")
        print(f"📈 Filter efficiency: {metadata['filter_efficiency']}")
        print(f"💾 Cache file: {cache_file}")
        print("="*60)

if __name__ == '__main__':
    main()
