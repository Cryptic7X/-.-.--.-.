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

def load_blocked_coins():
    """Load blocked coins from config file"""
    blocked = set()
    
    try:
        with open('config/blocked_coins.txt', 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#'):
                    blocked.add(line.upper())
    except FileNotFoundError:
        print("Warning: blocked_coins.txt not found")
    
    return blocked

def is_coin_blocked(symbol, blocked_coins):
    """Check if coin should be blocked"""
    symbol = symbol.upper()
    
    # Direct match
    if symbol in blocked_coins:
        return True
    
    # Pattern matching for USD-related coins
    usd_patterns = ['USD', 'BUSD', 'TUSD', 'FDUSD']
    for pattern in usd_patterns:
        if pattern in symbol and symbol != 'USDT':
            return True
    
    return False

def apply_filters(coins, config):
    """
    Apply single market filter: 100M+ market cap & 30M+ volume
    Returns single list of qualifying coins (~175 coins)
    """
    blocked_coins = load_blocked_coins()
    qualifying_coins = []
    
    min_market_cap = config['filters']['min_market_cap']
    min_volume = config['filters']['min_volume_24h']
    
    blocked_count = 0
    no_data_count = 0
    
    for coin in coins:
        symbol = coin.get('symbol', '').upper()
        market_cap = coin.get('market_cap') or 0
        volume_24h = coin.get('total_volume') or 0
        
        # Skip blocked coins
        if is_coin_blocked(symbol, blocked_coins):
            blocked_count += 1
            continue
        
        # Skip coins with insufficient data
        if not market_cap or not volume_24h:
            no_data_count += 1
            continue
        
        # Apply single filter criteria
        if market_cap >= min_market_cap and volume_24h >= min_volume:
            qualifying_coins.append(coin)
    
    print(f"Filter results:")
    print(f"  - Qualifying coins: {len(qualifying_coins)}")
    print(f"  - Blocked coins: {blocked_count}")
    print(f"  - No data coins: {no_data_count}")
    print(f"  - Total coins processed: {len(coins)}")
    
    return qualifying_coins
