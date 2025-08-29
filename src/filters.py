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

"""
Professional Market Filter System
Implements quality-based coin filtering for 4H analysis
"""

def load_blocked_coins():
    """Load professionally curated blocked coins list"""
    blocked = set()
    
    try:
        with open('config/blocked_coins.txt', 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#'):
                    blocked.add(line.upper())
    except FileNotFoundError:
        print("⚠️ Warning: blocked_coins.txt not found")
    
    return blocked

def is_professionally_blocked(symbol, blocked_coins):
    """Professional coin blocking with pattern recognition"""
    symbol = symbol.upper()
    
    # Direct exclusions
    if symbol in blocked_coins:
        return True
    
    # Stablecoin patterns
    stable_patterns = ['USD', 'USDT', 'USDC', 'BUSD', 'TUSD', 'FDUSD', 'DAI']
    for pattern in stable_patterns:
        if pattern in symbol and symbol != 'USDT':
            return True
    
    # Wrapped token patterns
    wrapped_patterns = ['WBTC', 'WETH', 'WBNB']
    if symbol in wrapped_patterns:
        return True
    
    return False

def validate_coin_data_quality(coin):
    """Validate coin data quality for professional analysis"""
    required_fields = ['symbol', 'market_cap', 'total_volume', 'current_price']
    
    for field in required_fields:
        if not coin.get(field):
            return False, f"Missing {field}"
    
    # Price validation
    price = coin.get('current_price', 0)
    if price <= 0 or price > 1000000:  # Reasonable price range
        return False, f"Invalid price: ${price}"
    
    # Volume validation
    volume = coin.get('total_volume', 0)
    if volume <= 0:
        return False, "Invalid volume"
    
    return True, "Valid"

def apply_professional_filters(coins, config):
    """
    Apply professional-grade market filters
    Returns high-quality coins suitable for 4H analysis
    """
    blocked_coins = load_blocked_coins()
    qualifying_coins = []
    
    # Filter criteria
    min_market_cap = config['market_filter']['min_market_cap']
    min_volume = config['market_filter']['min_volume_24h']
    
    # Statistics tracking
    stats = {
        'total_processed': len(coins),
        'blocked': 0,
        'invalid_data': 0,
        'below_market_cap': 0,
        'below_volume': 0,
        'qualified': 0
    }
    
    print(f"\n🔍 Applying professional filters...")
    print(f"📊 Criteria: Market Cap ≥ ${min_market_cap/1_000_000:.0f}M, Volume ≥ ${min_volume/1_000_000:.0f}M")
    
    for coin in coins:
        symbol = coin.get('symbol', '').upper()
        market_cap = coin.get('market_cap') or 0
        volume_24h = coin.get('total_volume') or 0
        
        # Professional blocking
        if is_professionally_blocked(symbol, blocked_coins):
            stats['blocked'] += 1
            continue
        
        # Data quality validation
        is_valid, reason = validate_coin_data_quality(coin)
        if not is_valid:
            stats['invalid_data'] += 1
            continue
        
        # Market cap filter
        if market_cap < min_market_cap:
            stats['below_market_cap'] += 1
            continue
        
        # Volume filter
        if volume_24h < min_volume:
            stats['below_volume'] += 1
            continue
        
        # Qualified coin
        qualifying_coins.append(coin)
        stats['qualified'] += 1
    
    # Professional reporting
    print(f"\n📋 PROFESSIONAL FILTER RESULTS:")
    print(f"   ✅ Qualified coins: {stats['qualified']}")
    print(f"   🚫 Blocked coins: {stats['blocked']}")
    print(f"   📊 Below market cap: {stats['below_market_cap']}")
    print(f"   📈 Below volume: {stats['below_volume']}")
    print(f"   ❌ Invalid data: {stats['invalid_data']}")
    print(f"   📊 Total processed: {stats['total_processed']}")
    print(f"   🎯 Success rate: {stats['qualified']/stats['total_processed']*100:.1f}%")
    
    return qualifying_coins
