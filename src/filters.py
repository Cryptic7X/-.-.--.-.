"""
Market Filters Module
====================

Handles filtering of cryptocurrency data based on:
- Market capitalization criteria  
- Volume requirements
- Blocked coins exclusion
- Symbol validation

Creates two filtered lists:
- Standard: High market cap, established coins
- High-Risk: Mid market cap, emerging opportunities
"""

import os
import yaml
from typing import List, Dict, Any


class MarketFilter:
    """
    Market-based cryptocurrency filtering system
    """
    
    def __init__(self, config_path='config/config.yaml'):
        """
        Initialize MarketFilter with configuration
        
        Args:
            config_path: Path to configuration YAML file
        """
        
        self.config = self._load_config(config_path)
        self.blocked_coins = self._load_blocked_coins()
        
        # Filter criteria from config
        self.standard_criteria = self.config['market_filters']['standard']
        self.high_risk_criteria = self.config['market_filters']['high_risk']
        
    def _load_config(self, config_path):
        """Load configuration from YAML file"""
        try:
            with open(config_path, 'r') as f:
                return yaml.safe_load(f)
        except Exception as e:
            print(f"Config loading error: {e}")
            # Return default criteria
            return {
                'market_filters': {
                    'standard': {
                        'market_cap_min': 500_000_000,
                        'volume_24h_min': 30_000_000
                    },
                    'high_risk': {
                        'market_cap_min': 10_000_000,
                        'market_cap_max': 500_000_000,
                        'volume_24h_min': 10_000_000
                    }
                }
            }
    
    def _load_blocked_coins(self, blocked_file='config/blocked_coins.txt'):
        """
        Load blocked coins from text file
        
        Args:
            blocked_file: Path to blocked coins file
            
        Returns:
            set: Set of blocked coin symbols (uppercase)
        """
        
        blocked_coins = set()
        
        if not os.path.exists(blocked_file):
            print(f"Blocked coins file not found: {blocked_file}")
            return blocked_coins
        
        try:
            with open(blocked_file, 'r') as f:
                for line in f:
                    line = line.strip()
                    
                    # Skip empty lines and comments
                    if line and not line.startswith('#'):
                        blocked_coins.add(line.upper())
            
            print(f"Loaded {len(blocked_coins)} blocked coins")
            return blocked_coins
            
        except Exception as e:
            print(f"Error loading blocked coins: {e}")
            return blocked_coins
    
    def is_blocked(self, symbol):
        """
        Check if coin symbol is blocked
        
        Args:
            symbol: Coin symbol to check
            
        Returns:
            bool: True if blocked
        """
        
        if not symbol:
            return True
            
        clean_symbol = str(symbol).upper().strip()
        
        # Direct match
        if clean_symbol in self.blocked_coins:
            return True
        
        # Pattern matching for common patterns
        blocked_patterns = ['USD', 'BUSD', 'USDT', 'USDC']
        for pattern in blocked_patterns:
            if pattern in clean_symbol and len(clean_symbol) <= len(pattern) + 2:
                return True
        
        return False
    
    def meets_standard_criteria(self, coin_data):
        """
        Check if coin meets standard filter criteria
        
        Args:
            coin_data: Dictionary with coin market data
            
        Returns:
            bool: True if meets criteria
        """
        
        try:
            market_cap = coin_data.get('market_cap', 0) or 0
            volume_24h = coin_data.get('total_volume', 0) or 0
            
            return (
                market_cap >= self.standard_criteria['market_cap_min'] and
                volume_24h >= self.standard_criteria['volume_24h_min']
            )
            
        except (TypeError, KeyError) as e:
            return False
    
    def meets_high_risk_criteria(self, coin_data):
        """
        Check if coin meets high-risk filter criteria
        
        Args:
            coin_data: Dictionary with coin market data
            
        Returns:
            bool: True if meets criteria
        """
        
        try:
            market_cap = coin_data.get('market_cap', 0) or 0
            volume_24h = coin_data.get('total_volume', 0) or 0
            
            return (
                self.high_risk_criteria['market_cap_min'] <= market_cap < self.high_risk_criteria['market_cap_max'] and
                volume_24h >= self.high_risk_criteria['volume_24h_min']
            )
            
        except (TypeError, KeyError) as e:
            return False
    
    def filter_coins(self, market_data):
        """
        Filter coins into standard and high-risk categories
        
        Args:
            market_data: List of coin market data dictionaries
            
        Returns:
            dict: Contains 'standard' and 'high_risk' filtered coin lists
        """
        
        if not market_data:
            return {'standard': [], 'high_risk': []}
        
        standard_coins = []
        high_risk_coins = []
        
        blocked_count = 0
        no_data_count = 0
        
        for coin in market_data:
            try:
                symbol = coin.get('symbol', '').upper()
                
                # Skip blocked coins
                if self.is_blocked(symbol):
                    blocked_count += 1
                    continue
                
                # Skip coins with missing essential data
                if not coin.get('market_cap') or not coin.get('total_volume'):
                    no_data_count += 1
                    continue
                
                # Apply filters
                if self.meets_standard_criteria(coin):
                    standard_coins.append(coin)
                elif self.meets_high_risk_criteria(coin):
                    high_risk_coins.append(coin)
                
            except Exception as e:
                print(f"Error processing coin {coin.get('symbol', 'UNKNOWN')}: {e}")
                continue
        
        print(f"Filter results:")
        print(f"  - Standard coins: {len(standard_coins)}")
        print(f"  - High-risk coins: {len(high_risk_coins)}")
        print(f"  - Blocked coins: {blocked_count}")
        print(f"  - No data coins: {no_data_count}")
        
        return {
            'standard': standard_coins,
            'high_risk': high_risk_coins,
            'stats': {
                'standard_count': len(standard_coins),
                'high_risk_count': len(high_risk_coins),
                'blocked_count': blocked_count,
                'no_data_count': no_data_count,
                'total_processed': len(market_data)
            }
        }
    
    def get_trading_symbols(self, filtered_coins, exchange='bingx'):
        """
        Convert filtered coins to trading symbols for exchange APIs
        
        Args:
            filtered_coins: Dictionary from filter_coins()
            exchange: Target exchange name
            
        Returns:
            dict: Trading symbols by category
        """
        
        def coin_to_symbol(coin):
            """Convert coin data to trading symbol"""
            symbol = coin.get('symbol', '').upper()
            return f"{symbol}/USDT"
        
        return {
            'standard': [coin_to_symbol(coin) for coin in filtered_coins['standard']],
            'high_risk': [coin_to_symbol(coin) for coin in filtered_coins['high_risk']]
        }
    
    def add_blocked_coin(self, symbol):
        """
        Add a coin to the blocked list
        
        Args:
            symbol: Coin symbol to block
        """
        
        clean_symbol = str(symbol).upper().strip()
        self.blocked_coins.add(clean_symbol)
        
        # Append to file
        try:
            with open('config/blocked_coins.txt', 'a') as f:
                f.write(f"\n{clean_symbol}")
            print(f"Added {clean_symbol} to blocked coins")
        except Exception as e:
            print(f"Error adding blocked coin: {e}")
    
    def remove_blocked_coin(self, symbol):
        """
        Remove a coin from the blocked list
        
        Args:
            symbol: Coin symbol to unblock
        """
        
        clean_symbol = str(symbol).upper().strip()
        if clean_symbol in self.blocked_coins:
            self.blocked_coins.remove(clean_symbol)
            print(f"Removed {clean_symbol} from blocked coins")
        
        # Note: This doesn't update the file automatically
        # Would need to rewrite the entire file
    
    def get_criteria_summary(self):
        """Get summary of filter criteria"""
        
        def format_currency(amount):
            """Format currency amount"""
            if amount >= 1_000_000_000:
                return f"${amount/1_000_000_000:.1f}B"
            elif amount >= 1_000_000:
                return f"${amount/1_000_000:.0f}M"
            else:
                return f"${amount:,.0f}"
        
        return {
            'standard': {
                'market_cap_min': format_currency(self.standard_criteria['market_cap_min']),
                'volume_24h_min': format_currency(self.standard_criteria['volume_24h_min']),
                'description': 'Established, high market cap cryptocurrencies'
            },
            'high_risk': {
                'market_cap_range': f"{format_currency(self.high_risk_criteria['market_cap_min'])} - {format_currency(self.high_risk_criteria['market_cap_max'])}",
                'volume_24h_min': format_currency(self.high_risk_criteria['volume_24h_min']),
                'description': 'Emerging, mid market cap cryptocurrencies'
            },
            'blocked_coins_count': len(self.blocked_coins)
        }


# Utility functions
def validate_coin_data(coin_data):
    """
    Validate that coin data has required fields
    
    Args:
        coin_data: Dictionary with coin data
        
    Returns:
        bool: True if valid
    """
    
    required_fields = ['symbol', 'market_cap', 'total_volume', 'current_price']
    
    try:
        for field in required_fields:
            if field not in coin_data or coin_data[field] is None:
                return False
        return True
    except:
        return False


def sort_coins_by_volume(coin_list):
    """
    Sort coins by 24h trading volume (descending)
    
    Args:
        coin_list: List of coin dictionaries
        
    Returns:
        list: Sorted coin list
    """
    
    try:
        return sorted(coin_list, key=lambda x: x.get('total_volume', 0), reverse=True)
    except:
        return coin_list


def get_market_cap_tier(market_cap):
    """
    Get market capitalization tier classification
    
    Args:
        market_cap: Market cap value
        
    Returns:
        str: Tier classification
    """
    
    if market_cap >= 10_000_000_000:  # $10B+
        return 'Large Cap'
    elif market_cap >= 2_000_000_000:  # $2B+
        return 'Mid Cap'  
    elif market_cap >= 300_000_000:  # $300M+
        return 'Small Cap'
    elif market_cap >= 50_000_000:  # $50M+
        return 'Micro Cap'
    else:
        return 'Nano Cap'
