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
        if pattern in symbol and symbol != 'USDT':  # Allow USDT pairs
            return True
    
    return False

def apply_filters(coins, config):
    """Apply market cap and volume filters"""
    blocked_coins = load_blocked_coins()
    standard_coins = []
    high_risk_coins = []
    
    std_config = config['filters']['standard']
    hr_config = config['filters']['high_risk']
    
    for coin in coins:
        symbol = coin.get('symbol', '').upper()
        market_cap = coin.get('market_cap') or 0
        volume_24h = coin.get('total_volume') or 0
        
        # Skip blocked coins
        if is_coin_blocked(symbol, blocked_coins):
            continue
        
        # Skip coins with insufficient data
        if not market_cap or not volume_24h:
            continue
        
        # Apply standard filter
        if (market_cap >= std_config['min_market_cap'] and 
            volume_24h >= std_config['min_volume_24h']):
            standard_coins.append(coin)
        
        # Apply high-risk filter
        elif (hr_config['min_market_cap'] <= market_cap < hr_config['max_market_cap'] and
              volume_24h >= hr_config['min_volume_24h']):
            high_risk_coins.append(coin)
    
    return standard_coins, high_risk_coins
