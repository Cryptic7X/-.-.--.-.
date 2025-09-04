#!/usr/bin/env python3
"""
Fixed Market Data Refresh System
- Uses personal CoinGecko API key correctly
- Higher filtering thresholds: market cap >= $100M, volume >= $20M
- Blocked coins from external text file
- Configurable pagination via config.yaml
- No daily Telegram success alerts
"""

import requests
import json
import os
import time
import yaml
from datetime import datetime, timedelta

class MarketDataRefresh:
    def __init__(self):
        self.api_key = os.getenv('COINGECKO_API_KEY', '')
        self.cache_dir = os.path.join(os.path.dirname(__file__), '..', '..', 'cache')
        self.config_dir = os.path.join(os.path.dirname(__file__), '..', '..', 'config')
        
        # Load configuration
        self.config = self.load_config()
        
        # File paths
        self.cache_file = os.path.join(self.cache_dir, 'high_risk_market_data.json')
        self.blocked_coins_file = os.path.join(self.config_dir, 'blocked_coins.txt')
        
        # Filtering criteria from config
        self.min_market_cap = self.config.get('market_data', {}).get('min_market_cap', 100_000_000)  # $100M
        self.min_volume_24h = self.config.get('market_data', {}).get('min_volume_24h', 20_000_000)   # $20M
        self.max_pages = self.config.get('market_data', {}).get('max_pages', 1)                      # 1 page = 250 coins
        self.per_page = 250  # CoinGecko standard
        
        self.blocked_coins = self.load_blocked_coins()
    
    def load_config(self):
        """Load configuration from config.yaml"""
        try:
            config_path = os.path.join(self.config_dir, 'config.yaml')
            with open(config_path, 'r') as f:
                return yaml.safe_load(f)
        except Exception as e:
            print(f"⚠️ Config load failed: {e}, using defaults")
            return {}
    
    def load_blocked_coins(self):
        """Load blocked coins from text file"""
        try:
            if os.path.exists(self.blocked_coins_file):
                with open(self.blocked_coins_file, 'r') as f:
                    blocked = [line.strip().lower() for line in f if line.strip() and not line.startswith('#')]
                print(f"📝 Loaded {len(blocked)} blocked coins from {self.blocked_coins_file}")
                return set(blocked)
            else:
                # Create default blocked coins file
                default_blocked = [
                    '# Stablecoins',
                    'tether',
                    'usd-coin', 
                    'binance-usd',
                    'dai',
                    'true-usd',
                    'frax',
                    'paxos-standard',
                    '# Failed/Risky Projects',
                    'terra-luna',
                    'terra-luna-2',
                    'ftx-token',
                    'celsius-degree-token',
                    '# Bitcoin Forks (often less reliable)',
                    'bitcoin-cash',
                    'bitcoin-sv',
                    'bitcoin-gold',
                    'bitcoin-diamond',
                    '# Low Quality/Scam Prone',
                    'safemoon',
                    'safemoon-2',
                ]
                
                os.makedirs(self.config_dir, exist_ok=True)
                with open(self.blocked_coins_file, 'w') as f:
                    f.write('\n'.join(default_blocked))
                
                # Return clean list without comments
                clean_blocked = [coin for coin in default_blocked if not coin.startswith('#')]
                print(f"📝 Created default blocked coins file: {len(clean_blocked)} coins")
                return set(clean_blocked)
                
        except Exception as e:
            print(f"⚠️ Error loading blocked coins: {e}")
            return set()
    
    def get_coingecko_headers(self):
        """Get headers for CoinGecko API requests"""
        headers = {
            'User-Agent': 'Dual-Confirmation-Bot/1.0',
            'Accept': 'application/json'
        }
        
        if self.api_key:
            headers['x-cg-demo-api-key'] = self.api_key  # Use demo API key header
            print("✅ Using CoinGecko API key")
        else:
            print("⚠️ No API key - using free tier (very limited)")
        
        return headers
    
    def fetch_coins_page(self, page=1):
        """Fetch one page of coins from CoinGecko using standard API"""
        # Use standard API endpoint (not pro)
        url = "https://api.coingecko.com/api/v3/coins/markets"
        
        params = {
            'vs_currency': 'usd',
            'order': 'market_cap_desc',
            'per_page': self.per_page,
            'page': page,
            'sparkline': 'false',
            'price_change_percentage': '24h'
        }
        
        headers = self.get_coingecko_headers()
        
        try:
            print(f"🔄 Fetching page {page} from CoinGecko...")
            response = requests.get(url, params=params, headers=headers, timeout=30)
            
            if response.status_code == 429:
                print("⚠️ Rate limited, waiting 60 seconds...")
                time.sleep(60)
                response = requests.get(url, params=params, headers=headers, timeout=30)
            
            response.raise_for_status()
            coins = response.json()
            
            print(f"✅ Page {page}: {len(coins)} coins fetched")
            
            # Rate limiting - be conservative
            time.sleep(6)  # 10 requests per minute for demo key
            
            return coins
            
        except requests.exceptions.RequestException as e:
            print(f"❌ Error fetching page {page}: {e}")
            if hasattr(e, 'response') and e.response is not None:
                print(f"   Response: {e.response.status_code} - {e.response.text[:200]}")
            return []
    
    def filter_coin(self, coin):
        """Apply filtering criteria to a single coin"""
        try:
            if not coin or not isinstance(coin, dict):
                return False, "Invalid coin data"
            
            coin_id = coin.get('id', '').lower()
            symbol = coin.get('symbol', '').upper()
            name = coin.get('name', '')
            market_cap = coin.get('market_cap') or 0
            volume_24h = coin.get('total_volume') or 0
            current_price = coin.get('current_price') or 0
            
            # Check blocked coins
            if coin_id in self.blocked_coins:
                return False, f"Blocked: {coin_id}"
            
            # Market cap filter (updated to $100M)
            if market_cap < self.min_market_cap:
                return False, f"Low market cap: ${market_cap:,.0f}"
            
            # Volume filter (updated to $20M)
            if volume_24h < self.min_volume_24h:
                return False, f"Low volume: ${volume_24h:,.0f}"
            
            # Price validation
            if current_price <= 0:
                return False, "Invalid price"
            
            # Symbol validation
            if len(symbol) < 2 or len(symbol) > 12:
                return False, f"Invalid symbol: {symbol}"
            
            return True, "Passed filters"
            
        except Exception as e:
            return False, f"Filter error: {e}"
    
    def refresh_market_data(self):
        """Main refresh method"""
        print("="*70)
        print("🔄 MARKET DATA REFRESH - FIXED VERSION")
        print("="*70)
        print(f"🕐 Started: {datetime.utcnow().isoformat()} UTC")
        print(f"🚫 Blocked coins: {len(self.blocked_coins)}")
        print(f"💰 Min market cap: ${self.min_market_cap:,}")
        print(f"📊 Min volume 24h: ${self.min_volume_24h:,}")
        print(f"📄 Max pages: {self.max_pages}")
        print(f"🔑 API key: {'Yes' if self.api_key else 'No'}")
        
        all_coins = []
        filtered_coins = []
        
        # Fetch pages
        for page in range(1, self.max_pages + 1):
            coins_page = self.fetch_coins_page(page)
            if not coins_page:
                print(f"❌ No data on page {page}, stopping")
                break
            
            all_coins.extend(coins_page)
            
            if len(coins_page) < self.per_page:
                print(f"ℹ️ Page {page} returned {len(coins_page)} coins (less than {self.per_page}), likely last page")
                break
        
        print(f"\n📊 Total coins fetched: {len(all_coins)}")
        
        # Apply filters
        print(f"🔍 Applying enhanced filters...")
        filter_stats = {}
        
        for coin in all_coins:
            passed, reason = self.filter_coin(coin)
            
            if passed:
                clean_coin = {
                    'id': coin.get('id', ''),
                    'symbol': coin.get('symbol', '').upper(),
                    'name': coin.get('name', ''),
                    'current_price': coin.get('current_price', 0),
                    'market_cap': coin.get('market_cap', 0),
                    'market_cap_rank': coin.get('market_cap_rank', 0),
                    'total_volume': coin.get('total_volume', 0),
                    'price_change_percentage_24h': coin.get('price_change_percentage_24h', 0),
                    'image': coin.get('image', ''),
                    'last_updated': coin.get('last_updated', ''),
                }
                filtered_coins.append(clean_coin)
            else:
                filter_type = reason.split(':')[0] if ':' in reason else reason
                filter_stats[filter_type] = filter_stats.get(filter_type, 0) + 1
        
        # Sort by market cap
        filtered_coins.sort(key=lambda x: x.get('market_cap', 0), reverse=True)
        
        # Save cache
        self.save_market_cache(filtered_coins, filter_stats)
        
        print(f"\n" + "="*70)
        print("✅ MARKET DATA REFRESH COMPLETE")
        print("="*70)
        print(f"📊 Fetched: {len(all_coins)} coins")
        print(f"✅ Filtered: {len(filtered_coins)} coins")
        print(f"🚫 Blocked: {filter_stats.get('Blocked', 0)}")
        print(f"💰 Low market cap: {filter_stats.get('Low market cap', 0)}")
        print(f"📉 Low volume: {filter_stats.get('Low volume', 0)}")
        print(f"💾 Cache saved: {len(filtered_coins)} coins")
        print("="*70)
        
        return len(filtered_coins)
    
    def save_market_cache(self, filtered_coins, filter_stats):
        """Save filtered coins to cache"""
        try:
            os.makedirs(self.cache_dir, exist_ok=True)
            
            cache_data = {
                'coins': filtered_coins,
                'metadata': {
                    'total_coins': len(filtered_coins),
                    'updated_at': datetime.utcnow().isoformat(),
                    'filter_criteria': {
                        'min_market_cap': self.min_market_cap,
                        'min_volume_24h': self.min_volume_24h,
                        'max_pages': self.max_pages,
                        'blocked_coins_count': len(self.blocked_coins)
                    },
                    'filter_stats': filter_stats,
                    'api_source': 'CoinGecko Standard API'
                }
            }
            
            with open(self.cache_file, 'w') as f:
                json.dump(cache_data, f, indent=2)
            
            print(f"💾 Cache saved: {self.cache_file}")
            
        except Exception as e:
            print(f"❌ Cache save failed: {e}")

if __name__ == '__main__':
    refresher = MarketDataRefresh()
    refresher.refresh_market_data()
