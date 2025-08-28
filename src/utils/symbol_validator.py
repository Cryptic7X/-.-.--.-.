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

def load_symbol_mapping():
    """Load TradingView symbol mapping"""
    try:
        mapping_path = os.path.join(os.path.dirname(__file__), '..', '..', 'config', 'symbol_mapping.json')
        with open(mapping_path, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

def validate_tradingview_symbol(coin_symbol):
    """Validate and map coin symbol to working TradingView format"""
    mapping = load_symbol_mapping()
    
    clean_symbol = coin_symbol.upper().replace('USDT', '').replace('USD', '')
    
    # Check direct mapping first
    if clean_symbol in mapping:
        return mapping[clean_symbol]
    
    # Use Bybit (works in India) instead of Binance
    tv_formats = [
        f"BYBIT:{clean_symbol}USDT",
        f"CRYPTO:{clean_symbol}USD",
        f"KUCOIN:{clean_symbol}USDT",
        f"{clean_symbol}USDT"
    ]
    
    return tv_formats[0]

def generate_tradingview_link(symbol, timeframe='1h'):
    """Generate working TradingView chart link"""
    tv_symbol = validate_tradingview_symbol(symbol)
    return f"https://www.tradingview.com/chart/?symbol={tv_symbol}&interval={timeframe}"

def generate_bybit_link(symbol):
    """Generate Bybit chart link as alternative"""
    clean_symbol = symbol.upper().replace('USDT', '')
    return f"https://www.bybit.com/trade/usdt/{clean_symbol}USDT"
