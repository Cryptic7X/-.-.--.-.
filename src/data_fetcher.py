"""
Data Fetcher Module
===================

Handles data fetching from multiple APIs:
- CoinGecko: Market cap and volume data (daily cache)
- BingX: Primary price/OHLCV data  
- CCXT: Fallback exchange data

Optimized for free API tier usage with intelligent caching.
"""

import requests
import pandas as pd
import numpy as np
import time
import json
import os
from datetime import datetime, timedelta
import ccxt
import yaml


class DataFetcher:
    """
    Multi-source cryptocurrency data fetcher with caching and fallback
    """
    
    def __init__(self, config_path='../config/config.yaml'):
        """
        Initialize DataFetcher with configuration
        
        Args:
            config_path: Path to configuration file
        """
        
        # Load configuration
        self.config = self._load_config(config_path)
        self.cache_dir = 'cache'
        self._ensure_cache_dir()
        
        # API endpoints and settings
        self.coingecko_base = self.config['apis']['coingecko']['base_url']
        self.coingecko_key = os.getenv('COINGECKO_API_KEY', '')
        
        # Rate limiting
        self.last_coingecko_call = 0
        self.coingecko_delay = 60 / self.config['apis']['coingecko']['requests_per_minute']
        
        # Initialize exchanges
        self._init_exchanges()
        
        # Cache settings
        self.cache_duration = self.config['data']['cache_duration_hours'] * 3600
        
    def _load_config(self, config_path):
        """Load configuration from YAML file"""
        try:
            with open(config_path, 'r') as f:
                return yaml.safe_load(f)
        except Exception as e:
            print(f"Config loading error: {e}")
            # Return default config
            return {
                'data': {'cache_duration_hours': 24, 'max_pages_coingecko': 6},
                'apis': {'coingecko': {'requests_per_minute': 50}}
            }
    
    def _ensure_cache_dir(self):
        """Create cache directory if it doesn't exist"""
        if not os.path.exists(self.cache_dir):
            os.makedirs(self.cache_dir)
    
    def _init_exchanges(self):
        """Initialize exchange connections"""
        self.exchanges = {}
        
        try:
            # BingX (primary)
            if 'bingx' in self.config['apis']:
                self.exchanges['bingx'] = ccxt.bingx({
                    'apiKey': os.getenv('BINGX_API_KEY', ''),
                    'secret': os.getenv('BINGX_API_SECRET', ''),
                    'sandbox': False,
                    'enableRateLimit': True,
                })
            
            # Binance (fallback)  
            self.exchanges['binance'] = ccxt.binance({
                'enableRateLimit': True,
            })
            
            # Bybit (fallback)
            self.exchanges['bybit'] = ccxt.bybit({
                'enableRateLimit': True,
            })
            
        except Exception as e:
            print(f"Exchange initialization warning: {e}")
    
    def _rate_limit_coingecko(self):
        """Enforce CoinGecko rate limiting"""
        now = time.time()
        elapsed = now - self.last_coingecko_call
        
        if elapsed < self.coingecko_delay:
            sleep_time = self.coingecko_delay - elapsed
            time.sleep(sleep_time)
        
        self.last_coingecko_call = time.time()
    
    def fetch_comprehensive_market_data(self, force_refresh=False):
        """
        Fetch comprehensive market data from CoinGecko (6 pages = 1,500 coins)
        Uses daily caching to optimize API usage
        
        Args:
            force_refresh: Force fresh data fetch ignoring cache
            
        Returns:
            list: Market data for all coins
        """
        
        cache_file = os.path.join(self.cache_dir, 'daily_market_data.json')
        
        # Check cache validity
        if not force_refresh and os.path.exists(cache_file):
            cache_age = time.time() - os.path.getmtime(cache_file)
            if cache_age < self.cache_duration:
                print("Loading market data from cache...")
                try:
                    with open(cache_file, 'r') as f:
                        return json.load(f)
                except Exception as e:
                    print(f"Cache loading error: {e}")
        
        print("Fetching fresh market data from CoinGecko...")
        all_coins = []
        
        max_pages = self.config['data'].get('max_pages_coingecko', 6)
        
        try:
            for page in range(1, max_pages + 1):
                print(f"Fetching page {page}/{max_pages}...")
                
                # Rate limiting
                self._rate_limit_coingecko()
                
                # Build URL
                url = f"{self.coingecko_base}/coins/markets"
                params = {
                    'vs_currency': 'usd',
                    'order': 'market_cap_desc',
                    'per_page': 250,
                    'page': page,
                    'sparkline': 'false'
                }
                
                if self.coingecko_key:
                    params['x-cg-demo-api-key'] = self.coingecko_key
                
                # Make request
                response = requests.get(url, params=params, timeout=30)
                response.raise_for_status()
                
                page_data = response.json()
                all_coins.extend(page_data)
                
                print(f"  -> Fetched {len(page_data)} coins")
                
                # Small delay between pages
                time.sleep(2)
            
            # Cache the results
            with open(cache_file, 'w') as f:
                json.dump(all_coins, f)
            
            print(f"Successfully fetched {len(all_coins)} coins from CoinGecko")
            return all_coins
            
        except Exception as e:
            print(f"CoinGecko fetch error: {str(e)}")
            
            # Try to return cached data as fallback
            if os.path.exists(cache_file):
                print("Returning cached data as fallback...")
                try:
                    with open(cache_file, 'r') as f:
                        return json.load(f)
                except:
                    pass
            
            return []
    
    def fetch_ohlcv_data(self, symbol, timeframe='1h', limit=100, exchange='bingx'):
        """
        Fetch OHLCV data from exchange
        
        Args:
            symbol: Trading pair symbol (e.g., 'BTC/USDT')
            timeframe: Timeframe for candles (default '1h')
            limit: Number of candles to fetch
            exchange: Preferred exchange (default 'bingx')
            
        Returns:
            pandas.DataFrame: OHLCV data with datetime index
        """
        
        exchange_list = [exchange] if exchange in self.exchanges else []
        exchange_list.extend([ex for ex in self.exchanges.keys() if ex != exchange])
        
        for ex_name in exchange_list:
            try:
                exchange_obj = self.exchanges[ex_name]
                
                # Fetch OHLCV data  
                ohlcv = exchange_obj.fetch_ohlcv(symbol, timeframe, limit=limit)
                
                if not ohlcv:
                    continue
                
                # Convert to DataFrame
                df = pd.DataFrame(ohlcv, columns=['timestamp', 'Open', 'High', 'Low', 'Close', 'Volume'])
                df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
                
                # Adjust to IST timezone (UTC+5:30)
                df['timestamp'] = df['timestamp'] + pd.Timedelta(hours=5, minutes=30)
                df.set_index('timestamp', inplace=True)
                
                print(f"Fetched {len(df)} candles for {symbol} from {ex_name}")
                return df
                
            except Exception as e:
                print(f"Failed to fetch {symbol} from {ex_name}: {str(e)}")
                continue
        
        print(f"Failed to fetch {symbol} from all exchanges")
        return None
    
    def get_available_symbols(self, exchange='bingx'):
        """
        Get list of available trading symbols from exchange
        
        Args:
            exchange: Exchange name
            
        Returns:
            list: Available symbols
        """
        
        try:
            if exchange in self.exchanges:
                markets = self.exchanges[exchange].load_markets()
                return list(markets.keys())
        except Exception as e:
            print(f"Error fetching symbols from {exchange}: {e}")
        
        return []
    
    def validate_symbol(self, symbol, exchange='bingx'):
        """
        Check if symbol is available on exchange
        
        Args:
            symbol: Trading pair symbol
            exchange: Exchange name
            
        Returns:
            bool: True if symbol exists
        """
        
        try:
            if exchange in self.exchanges:
                markets = self.exchanges[exchange].load_markets()
                return symbol in markets
        except Exception as e:
            print(f"Symbol validation error: {e}")
        
        return False
    
    def get_cache_stats(self):
        """Get cache statistics"""
        cache_file = os.path.join(self.cache_dir, 'daily_market_data.json')
        
        stats = {
            'cache_exists': os.path.exists(cache_file),
            'cache_age_hours': 0,
            'next_refresh_hours': 0
        }
        
        if stats['cache_exists']:
            cache_age_seconds = time.time() - os.path.getmtime(cache_file)
            stats['cache_age_hours'] = cache_age_seconds / 3600
            stats['next_refresh_hours'] = max(0, (self.cache_duration - cache_age_seconds) / 3600)
        
        return stats


# Utility functions
def normalize_symbol(coin_symbol):
    """
    Normalize coin symbol to standard format for exchange APIs
    
    Args:
        coin_symbol: Coin symbol (e.g., 'bitcoin', 'BTC')
        
    Returns:
        str: Normalized symbol (e.g., 'BTC/USDT')
    """
    
    # Common symbol mappings
    symbol_map = {
        'bitcoin': 'BTC',
        'ethereum': 'ETH',
        'binancecoin': 'BNB',
        'cardano': 'ADA',
        'solana': 'SOL',
        'ripple': 'XRP',
        'polkadot': 'DOT',
        'dogecoin': 'DOGE',
    }
    
    # Convert to uppercase and clean
    clean_symbol = str(coin_symbol).upper().strip()
    
    # Check if it's a CoinGecko ID
    if clean_symbol.lower() in symbol_map:
        clean_symbol = symbol_map[clean_symbol.lower()]
    
    # Add USDT pair if not present
    if '/' not in clean_symbol:
        clean_symbol = f"{clean_symbol}/USDT"
    
    return clean_symbol


def symbol_to_coingecko_id(symbol):
    """
    Convert trading symbol back to CoinGecko ID format
    
    Args:
        symbol: Trading symbol (e.g., 'BTC/USDT')
        
    Returns:
        str: CoinGecko ID (e.g., 'bitcoin')
    """
    
    # Remove pair suffix  
    base_symbol = symbol.replace('/USDT', '').replace('/USD', '').upper()
    
    # Common reverse mappings
    id_map = {
        'BTC': 'bitcoin',
        'ETH': 'ethereum', 
        'BNB': 'binancecoin',
        'ADA': 'cardano',
        'SOL': 'solana',
        'XRP': 'ripple',
        'DOT': 'polkadot',
        'DOGE': 'dogecoin',
    }
    
    return id_map.get(base_symbol, base_symbol.lower())
