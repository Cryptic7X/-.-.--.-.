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
import time
import json
import os
import ccxt
import yaml


class DataFetcher:
    def __init__(self, config_path='../config/config.yaml'):
        # Load configuration
        self.config = self._load_config(config_path)
        self.cache_dir = 'src/cache'
        os.makedirs(self.cache_dir, exist_ok=True)

        # CoinGecko settings
        cg_cfg = self.config['apis']['coingecko']
        self.coingecko_base = cg_cfg['base_url']
        self.coingecko_key = os.getenv('COINGECKO_API_KEY', '')
        self.rate_limit_per_min = cg_cfg.get('requests_per_minute', 50)
        self.min_delay = 60 / self.rate_limit_per_min
        self.last_call = 0

        # Initialize exchanges (same as before)...
        self._init_exchanges()

    def _load_config(self, path):
        with open(path) as f:
            return yaml.safe_load(f)

    def _init_exchanges(self):
        self.exchanges = {}
        try:
            self.exchanges['bingx'] = ccxt.bingx({'enableRateLimit': True})
        except: pass
        for ex in ['binance', 'bybit']:
            try:
                self.exchanges[ex] = getattr(ccxt, ex)({'enableRateLimit': True})
            except: pass

    def _rate_limit(self):
        elapsed = time.time() - self.last_call
        if elapsed < self.min_delay:
            time.sleep(self.min_delay - elapsed)
        self.last_call = time.time()

    def fetch_comprehensive_market_data(self):
        cache_file = os.path.join(self.cache_dir, 'daily_market_data.json')
        max_pages = self.config['data']['max_pages_coingecko']
        all_coins = []

        for page in range(1, max_pages+1):
            retries = 3
            while retries:
                try:
                    self._rate_limit()
                    params = {
                        'vs_currency': 'usd',
                        'order': 'market_cap_desc',
                        'per_page': 250,
                        'page': page,
                        'sparkline': 'false'
                    }
                    if self.coingecko_key:
                        params['x-cg-demo-api-key'] = self.coingecko_key
                    resp = requests.get(f"{self.coingecko_base}/coins/markets", params=params, timeout=30)
                    resp.raise_for_status()
                    page_data = resp.json()
                    all_coins.extend(page_data)
                    break
                except requests.exceptions.HTTPError as e:
                    if resp.status_code == 429:
                        wait = 60  # wait a minute then retry
                        print(f"Rate limit hit on page {page}, waiting {wait}s...")
                        time.sleep(wait)
                        retries -= 1
                    else:
                        print(f"Unexpected HTTP error on page {page}: {e}")
                        retries = 0
                except Exception as e:
                    print(f"Error fetching page {page}: {e}")
                    retries = 0

        if not all_coins and os.path.exists(cache_file):
            print("No new data; loading cached market data")
            return json.load(open(cache_file))

        # Cache results (even partial)
        with open(cache_file, 'w') as f:
            json.dump(all_coins, f)

        return all_coins

    
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
