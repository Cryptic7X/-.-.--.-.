"""
Symbol Validator and TradingView Link Generator
==============================================

Validates cryptocurrency symbols and generates working TradingView chart links.
Prevents invalid symbol errors by using fallback mapping and format testing.

Features:
- Symbol validation across multiple exchanges
- TradingView link generation with fallback formats
- Symbol mapping for common mismatches
- Exchange preference handling
"""

import json
import os
import yaml
from typing import Optional, List


class SymbolValidator:
    """
    Symbol Validator and TradingView Link Generator
    
    Ensures TradingView chart links work properly by validating symbols
    and providing fallback formats when needed.
    """
    
    def __init__(self, config_path='../config/config.yaml'):
        """
        Initialize symbol validator
        
        Args:
            config_path: Path to configuration file
        """
        
        self.config = self._load_config(config_path)
        self.symbol_mappings = self._load_symbol_mappings()
        
        # TradingView link settings
        self.tv_base_url = "https://www.tradingview.com/chart/"
        self.default_exchange = "BINANCE"
        self.default_interval = "1h"
        
    def _load_config(self, config_path):
        """Load configuration from YAML file"""
        try:
            with open(config_path, 'r') as f:
                return yaml.safe_load(f)
        except Exception as e:
            print(f"Config loading error: {e}")
            return {}
    
    def _load_symbol_mappings(self):
        """Load symbol mappings from JSON file"""
        mapping_file = 'config/symbol_mapping.json'
        
        if os.path.exists(mapping_file):
            try:
                with open(mapping_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                print(f"Symbol mapping loading error: {e}")
        
        # Default mappings if file doesn't exist
        return {
            "symbol_mappings": {
                "BTC": "BTCUSDT",
                "ETH": "ETHUSDT",
                "BNB": "BNBUSDT"
            },
            "exchange_preferences": ["BINANCE", "BYBIT", "BINGX"],
            "fallback_formats": [
                "{exchange}:{symbol}USDT",
                "{symbol}USDT",
                "{symbol}USD",
                "CRYPTO:{symbol}USD"
            ],
            "invalid_symbols": ["USDT", "USDC", "BUSD"]
        }
    
    def normalize_symbol(self, symbol):
        """
        Normalize symbol to standard format
        
        Args:
            symbol: Raw symbol (e.g., 'BTC', 'bitcoin')
            
        Returns:
            str: Normalized symbol (e.g., 'BTC')
        """
        
        if not symbol:
            return None
        
        # Convert to uppercase and clean
        clean_symbol = str(symbol).upper().strip()
        
        # Remove common suffixes
        for suffix in ['/USDT', '/USD', 'USDT', 'USD']:
            if clean_symbol.endswith(suffix):
                clean_symbol = clean_symbol[:-len(suffix)]
                break
        
        # Check symbol mappings
        mappings = self.symbol_mappings.get("symbol_mappings", {})
        if clean_symbol in mappings:
            return mappings[clean_symbol].replace('USDT', '')
        
        return clean_symbol
    
    def is_valid_symbol(self, symbol):
        """
        Check if symbol is valid for trading
        
        Args:
            symbol: Symbol to validate
            
        Returns:
            bool: True if valid
        """
        
        if not symbol:
            return False
        
        normalized = self.normalize_symbol(symbol)
        
        # Check against invalid symbols list
        invalid_symbols = self.symbol_mappings.get("invalid_symbols", [])
        if normalized in invalid_symbols:
            return False
        
        # Basic validation rules
        if len(normalized) < 2 or len(normalized) > 10:
            return False
        
        # Check for numeric-only symbols (usually invalid)
        if normalized.isdigit():
            return False
        
        return True
    
    def get_tradingview_symbol(self, symbol, exchange=None):
        """
        Get properly formatted TradingView symbol
        
        Args:
            symbol: Base symbol
            exchange: Preferred exchange (optional)
            
        Returns:
            str: TradingView formatted symbol
        """
        
        if not self.is_valid_symbol(symbol):
            return None
        
        normalized = self.normalize_symbol(symbol)
        
        # Use provided exchange or default
        target_exchange = exchange or self.default_exchange
        
        # Try different formats based on fallback list
        fallback_formats = self.symbol_mappings.get("fallback_formats", [])
        
        for format_template in fallback_formats:
            try:
                tv_symbol = format_template.format(
                    exchange=target_exchange,
                    symbol=normalized
                )
                return tv_symbol
            except:
                continue
        
        # Final fallback
        return f"{target_exchange}:{normalized}USDT"
    
    def get_tradingview_link(self, symbol, exchange=None, interval=None):
        """
        Generate TradingView chart link
        
        Args:
            symbol: Cryptocurrency symbol
            exchange: Exchange preference (optional)
            interval: Chart interval (optional, default '1h')
            
        Returns:
            str: Complete TradingView chart URL
        """
        
        if not self.is_valid_symbol(symbol):
            # Return fallback link
            return f"{self.tv_base_url}?symbol=BINANCE:BTCUSDT&interval=1h"
        
        # Get TradingView symbol
        tv_symbol = self.get_tradingview_symbol(symbol, exchange)
        if not tv_symbol:
            # Fallback to BTC chart
            return f"{self.tv_base_url}?symbol=BINANCE:BTCUSDT&interval=1h"
        
        # Use provided interval or default
        chart_interval = interval or self.default_interval
        
        # Build URL
        url = f"{self.tv_base_url}?symbol={tv_symbol}&interval={chart_interval}"
        
        return url
    
    def test_symbol_formats(self, symbol):
        """
        Test multiple symbol formats for debugging
        
        Args:
            symbol: Symbol to test
            
        Returns:
            dict: Test results for different formats
        """
        
        normalized = self.normalize_symbol(symbol)
        exchange_preferences = self.symbol_mappings.get("exchange_preferences", ["BINANCE"])
        fallback_formats = self.symbol_mappings.get("fallback_formats", [])
        
        test_results = {
            'original_symbol': symbol,
            'normalized_symbol': normalized,
            'is_valid': self.is_valid_symbol(symbol),
            'formats_tested': []
        }
        
        # Test all combinations
        for exchange in exchange_preferences:
            for format_template in fallback_formats:
                try:
                    tv_symbol = format_template.format(
                        exchange=exchange,
                        symbol=normalized
                    )
                    
                    test_results['formats_tested'].append({
                        'exchange': exchange,
                        'format': format_template,
                        'result': tv_symbol,
                        'url': f"{self.tv_base_url}?symbol={tv_symbol}&interval=1h"
                    })
                except:
                    continue
        
        return test_results
    
    def add_symbol_mapping(self, symbol, trading_view_symbol):
        """
        Add a new symbol mapping
        
        Args:
            symbol: Original symbol
            trading_view_symbol: TradingView format symbol
        """
        
        mappings = self.symbol_mappings.get("symbol_mappings", {})
        mappings[symbol.upper()] = trading_view_symbol.upper()
        
        # Save updated mappings
        try:
            with open('config/symbol_mapping.json', 'w') as f:
                json.dump(self.symbol_mappings, f, indent=2)
            print(f"Added mapping: {symbol} -> {trading_view_symbol}")
        except Exception as e:
            print(f"Error saving symbol mapping: {e}")
    
    def validate_batch_symbols(self, symbol_list):
        """
        Validate a batch of symbols
        
        Args:
            symbol_list: List of symbols to validate
            
        Returns:
            dict: Validation results
        """
        
        results = {
            'valid_symbols': [],
            'invalid_symbols': [],
            'mappings_needed': [],
            'total_tested': len(symbol_list)
        }
        
        for symbol in symbol_list:
            if self.is_valid_symbol(symbol):
                tv_symbol = self.get_tradingview_symbol(symbol)
                if tv_symbol:
                    results['valid_symbols'].append({
                        'symbol': symbol,
                        'tv_symbol': tv_symbol,
                        'link': self.get_tradingview_link(symbol)
                    })
                else:
                    results['mappings_needed'].append(symbol)
            else:
                results['invalid_symbols'].append(symbol)
        
        return results
    
    def get_symbol_stats(self):
        """Get symbol validation statistics"""
        
        mappings = self.symbol_mappings.get("symbol_mappings", {})
        invalid_symbols = self.symbol_mappings.get("invalid_symbols", [])
        
        return {
            'total_mappings': len(mappings),
            'invalid_symbols_count': len(invalid_symbols),
            'supported_exchanges': len(self.symbol_mappings.get("exchange_preferences", [])),
            'fallback_formats_count': len(self.symbol_mappings.get("fallback_formats", []))
        }


# Test functions
def test_symbol_validator():
    """Test the symbol validator"""
    
    validator = SymbolValidator()
    
    print("=== Symbol Validator Test ===")
    
    # Test symbols
    test_symbols = ['BTC', 'ETH', 'DOGE', 'SHIB', 'INVALID123', 'USDT']
    
    for symbol in test_symbols:
        print(f"\nTesting: {symbol}")
        print(f"  Valid: {validator.is_valid_symbol(symbol)}")
        print(f"  Normalized: {validator.normalize_symbol(symbol)}")
        print(f"  TV Symbol: {validator.get_tradingview_symbol(symbol)}")
        print(f"  TV Link: {validator.get_tradingview_link(symbol)}")
    
    # Batch validation
    print(f"\n=== Batch Validation ===")
    results = validator.validate_batch_symbols(test_symbols)
    
    print(f"Valid: {len(results['valid_symbols'])}")
    print(f"Invalid: {len(results['invalid_symbols'])}")
    print(f"Need mapping: {len(results['mappings_needed'])}")
    
    # Statistics
    print(f"\n=== Statistics ===")
    stats = validator.get_symbol_stats()
    for key, value in stats.items():
        print(f"{key}: {value}")


if __name__ == "__main__":
    test_symbol_validator()
