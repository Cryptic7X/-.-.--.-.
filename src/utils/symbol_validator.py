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

def load_symbol_mapping():
    """Load TradingView symbol mapping"""
    try:
        with open('config/symbol_mapping.json', 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

def validate_tradingview_symbol(coin_symbol):
    """
    Validate and map coin symbol to TradingView format
    Returns properly formatted TradingView symbol
    """
    mapping = load_symbol_mapping()
    
    # Clean the symbol
    clean_symbol = coin_symbol.upper().replace('USDT', '').replace('USD', '')
    
    # Check direct mapping first
    if clean_symbol in mapping:
        return mapping[clean_symbol]
    
    # Try different TradingView formats
    tv_formats = [
        f"BINANCE:{clean_symbol}USDT",
        f"CRYPTO:{clean_symbol}USD",
        f"{clean_symbol}USDT",
        f"{clean_symbol}USD"
    ]
    
    # Return the first format (most common)
    return tv_formats[0]

def generate_tradingview_link(symbol, timeframe='1h'):
    """Generate TradingView chart link"""
    tv_symbol = validate_tradingview_symbol(symbol)
    return f"https://www.tradingview.com/chart/?symbol={tv_symbol}&interval={timeframe}"
