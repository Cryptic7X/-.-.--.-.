#!/usr/bin/env python3
"""
Market Data Refresh System
- Fetches coins from CoinGecko API
- Filters by market cap, volume, and other criteria
- Excludes blocked/blacklisted coins
- Saves filtered coin universe to cache
"""

import requests
import json
import os
import time
from datetime import datetime, timedelta

class MarketDataRefresh:
    def __init__(self):
        self.api_key = os.getenv('COINGECKO_API_KEY', '')
        self.cache_dir = os.path.join(os.path.dirname(__file__), '..', '..', 'cache')
        self.cache_file = os.path.join(self.cache_dir, 'high_risk_market_data.json')
        self.blocked_coins_file = os.path.join(self.cache_dir, 'blocked_coins.json')
        
        # Filtering criteria
        self.min_market_cap = 50_000_000  # $50M minimum
        self.min_volume_24h = 5_000_000   # $5M minimum daily volume
        self.max_coins = 500              # Top 500 coins max
        self.per_page = 250               # API pagination
        
        self.blocked_coins = self.load_blocked_coins()
    
    def load_blocked_coins(self):
        """Load blocked/blacklisted coins"""
        try:
            if os.path.exists(self.blocked_coins_file):
                with open(self.blocked_coins_file, 'r') as f:
                    data = json.load(f)
                blocked = data.get('blocked_coins', [])
                print(f"📝 Loaded {len(blocked)} blocked coins")
                return set(blocked)
            else:
                # Default blocked coins if file doesn't exist
                default_blocked = [
                    'tether', 'usd-coin', 'binance-usd', 'dai', 'true-usd', 'paxos-standard',
                    'gemini-dollar', 'frax', 'terrausd', 'neutrino', 'magic-internet-money',
                    'fei-usd', 'liquity-usd', 'alchemix-usd', 'olympus', 'wonderland',
                    'bitcoin-cash-sv', 'bitcoin-gold', 'bitcoin-diamond', 'bitcoin-private'
                ]
                
                # Save default blocked coins
                self.save_blocked_coins(default_blocked)
                return set(default_blocked)
        except Exception as e:
            print(f"⚠️ Error loading blocked coins: {e}")
            return set()
    
    def save_blocked_coins(self, blocked_list):
        """Save blocked coins list"""
        try:
            os.makedirs(self.cache_dir, exist_ok=True)
            data = {
                'blocked_coins': list(blocked_list),
                'updated_at': datetime.utcnow().isoformat(),
                'total_blocked': len(blocked_list)
            }
            with open(self.blocked_coins_file, 'w') as f:
                json.dump(data, f, indent=2)
            print(f"💾 Saved {len(blocked_list)} blocked coins")
        except Exception as e:
            print(f"❌ Error saving blocked coins: {e}")
    
    def get_coingecko_headers(self):
        """Get headers for CoinGecko API requests"""
        headers = {
            'User-Agent': 'Dual-Confirmation-Bot/1.0',
            'Accept': 'application/json'
        }
        
        if self.api_key:
            headers['x-cg-pro-api-key'] = self.api_key
            print("✅ Using CoinGecko Pro API key")
        else:
            print("⚠️ Using CoinGecko Free API (rate limited)")
        
        return headers
    
    def fetch_coins_page(self, page=1):
        """Fetch one page of coins from CoinGecko"""
        base_url = "https://pro-api.coingecko.com/api/v3" if self.api_key else "https://api.coingecko.com/api/v3"
        url = f"{base_url}/coins/markets"
        
        params = {
            'vs_currency': 'usd',
            'order': 'market_cap_desc',
            'per_page': self.per_page,
            'page': page,
            'sparkline': 'false',
            'price_change_percentage': '24h',
            'locale': 'en'
        }
        
        headers = self.get_coingecko_headers()
        
        try:
            response = requests.get(url, params=params, headers=headers, timeout=30)
            response.raise_for_status()
            
            coins = response.json()
            print(f"📊 Fetched page {page}: {len(coins)} coins")
            
            # Rate limiting
            if not self.api_key:  # Free API needs more conservative rate limiting
                time.sleep(2)
            else:
                time.sleep(0.5)
            
            return coins
            
        except requests.exceptions.RequestException as e:
            print(f"❌ Error fetching page {page}: {e}")
            return []
    
    def filter_coin(self, coin):
        """Apply filtering criteria to a single coin"""
        try:
            # Basic data validation
            if not coin or not isinstance(coin, dict):
                return False, "Invalid coin data"
            
            coin_id = coin.get('id', '')
            symbol = coin.get('symbol', '').upper()
            name = coin.get('name', '')
            market_cap = coin.get('market_cap') or 0
            volume_24h = coin.get('total_volume') or 0
            current_price = coin.get('current_price') or 0
            
            # Check blocked coins
            if coin_id in self.blocked_coins:
                return False, f"Blocked coin: {coin_id}"
            
            # Market cap filter
            if market_cap < self.min_market_cap:
                return False, f"Market cap too low: ${market_cap:,.0f}"
            
            # Volume filter
            if volume_24h < self.min_volume_24h:
                return False, f"Volume too low: ${volume_24h:,.0f}"
            
            # Price filter (exclude very low prices that might be inactive)
            if current_price <= 0:
                return False, "Invalid price"
            
            # Basic symbol validation
            if len(symbol) < 2 or len(symbol) > 10:
                return False, f"Invalid symbol: {symbol}"
            
            return True, "Passed all filters"
            
        except Exception as e:
            return False, f"Filter error: {e}"
    
    def refresh_market_data(self):
        """Main method to refresh market data"""
        print("="*60)
        print("🔄 MARKET DATA REFRESH STARTING")
        print("="*60)
        print(f"🕐 Started at: {datetime.utcnow().isoformat()} UTC")
        print(f"🚫 Blocked coins: {len(self.blocked_coins)}")
        print(f"💰 Min market cap: ${self.min_market_cap:,}")
        print(f"📊 Min volume: ${self.min_volume_24h:,}")
        print(f"🔢 Max coins: {self.max_coins}")
        
        all_coins = []
        filtered_coins = []
        page = 1
        total_pages = (self.max_coins + self.per_page - 1) // self.per_page
        
        # Fetch coins from multiple pages
        while page <= total_pages:
            print(f"\n🔄 Processing page {page}/{total_pages}")
            
            coins_page = self.fetch_coins_page(page)
            if not coins_page:
                print(f"❌ No data on page {page}, stopping")
                break
            
            all_coins.extend(coins_page)
            page += 1
            
            # Stop if we have enough coins
            if len(all_coins) >= self.max_coins:
                all_coins = all_coins[:self.max_coins]
                break
        
        print(f"\n📊 Total coins fetched: {len(all_coins)}")
        
        # Filter coins
        print(f"\n🔍 Applying filters...")
        filter_stats = {}
        
        for coin in all_coins:
            passed, reason = self.filter_coin(coin)
            
            if passed:
                # Clean up coin data for storage
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
                # Track filter reasons for debugging
                filter_type = reason.split(':')[0] if ':' in reason else reason
                filter_stats[filter_type] = filter_stats.get(filter_type, 0) + 1
        
        # Sort by market cap
        filtered_coins.sort(key=lambda x: x.get('market_cap', 0), reverse=True)
        
        # Save to cache
        self.save_market_cache(filtered_coins, filter_stats)
        
        print(f"\n" + "="*60)
        print("✅ MARKET DATA REFRESH COMPLETE")
        print("="*60)
        print(f"📊 Total fetched: {len(all_coins)} coins")
        print(f"✅ Filtered coins: {len(filtered_coins)} coins")
        print(f"🚫 Blocked: {filter_stats.get('Blocked coin', 0)}")
        print(f"💰 Low market cap: {filter_stats.get('Market cap too low', 0)}")
        print(f"📉 Low volume: {filter_stats.get('Volume too low', 0)}")
        print(f"💾 Cache updated: {self.cache_file}")
        print("="*60)
        
        return len(filtered_coins)
    
    def save_market_cache(self, filtered_coins, filter_stats):
        """Save filtered coins to cache file"""
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
                        'max_coins': self.max_coins,
                        'blocked_coins_count': len(self.blocked_coins)
                    },
                    'filter_stats': filter_stats,
                    'api_source': 'CoinGecko Pro' if self.api_key else 'CoinGecko Free'
                }
            }
            
            with open(self.cache_file, 'w') as f:
                json.dump(cache_data, f, indent=2)
            
            print(f"💾 Saved {len(filtered_coins)} coins to cache")
            
        except Exception as e:
            print(f"❌ Error saving cache: {e}")

if __name__ == '__main__':
    refresher = MarketDataRefresh()
    refresher.refresh_market_data()
