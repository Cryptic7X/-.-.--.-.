"""
Main System Orchestration
=========================

Crypto Alert System main module that coordinates all components:
- Market data fetching and filtering
- Signal generation using validated CipherB indicator
- Stochastic RSI confirmation
- Alert deduplication and dispatch
- Error handling and logging

This is the entry point for both manual execution and automated GitHub Actions.
"""
#!/usr/bin/env python3
import json
import os
import sys
import time
import ccxt
import pandas as pd
import yaml
from datetime import datetime, timedelta

# Add current directory to Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

from utils.heikin_ashi import heikin_ashi
from indicators.cipherb_fixed import detect_cipherb_signals
from indicators.stoch_rsi import calculate_stoch_rsi, check_stoch_rsi_confirmation
from alerts.deduplication import AlertDeduplicator
from alerts.telegram_handler import send_telegram_alert

def load_config():
    """Load configuration"""
    config_path = os.path.join(os.path.dirname(__file__), '..', 'config', 'config.yaml')
    with open(config_path, 'r') as f:
        return yaml.safe_load(f)

def load_cached_coins():
    """Load cached coin data from daily scan"""
    cache_file = os.path.join(os.path.dirname(__file__), '..', 'cache', 'daily_coin_data.json')
    
    if not os.path.exists(cache_file):
        print("❌ No cached coin data found. Run daily scan first.")
        return None
    
    with open(cache_file, 'r') as f:
        data = json.load(f)
    
    return data.get('coins', [])

def initialize_exchanges():
    """Initialize exchanges - BingX primary"""
    exchanges = []
    
    # BingX (Primary - works well in India)
    try:
        bingx = ccxt.bingx({
            'apiKey': os.getenv('BINGX_API_KEY', ''),
            'secret': os.getenv('BINGX_SECRET_KEY', ''),
            'sandbox': False,
            'rateLimit': 200,
            'enableRateLimit': True,
        })
        exchanges.append(('BingX', bingx))
    except Exception as e:
        print(f"⚠️ BingX initialization failed: {e}")
    
    # KuCoin (Fallback)
    try:
        kucoin = ccxt.kucoin({
            'rateLimit': 1200,
            'enableRateLimit': True,
        })
        exchanges.append(('KuCoin', kucoin))
    except Exception as e:
        print(f"⚠️ KuCoin initialization failed: {e}")
    
    return exchanges

def fetch_price_data(symbol, exchanges):
    """Fetch 1-hour OHLCV data with IST timezone adjustment"""
    for exchange_name, exchange in exchanges:
        try:
            # Fetch 60 candles for better indicator accuracy
            ohlcv = exchange.fetch_ohlcv(f"{symbol}/USDT", '1h', limit=60)
            
            if len(ohlcv) < 30:
                continue
            
            # Convert to DataFrame
            df = pd.DataFrame(ohlcv, columns=['timestamp', 'Open', 'High', 'Low', 'Close', 'Volume'])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            df.set_index('timestamp', inplace=True)
            
            # CRITICAL: Adjust timezone to IST (UTC+5:30) to match TradingView
            df.index = df.index + pd.Timedelta(hours=5, minutes=30)
            
            return df
            
        except Exception as e:
            continue
    
    return None

def process_coin_signals(coin_data, deduplicator, exchanges, config):
    """Process a single coin for CipherB + StochRSI signals"""
    symbol = coin_data.get('symbol', '').upper()
    alert_sent = False
    
    try:
        # Fetch price data
        price_df = fetch_price_data(symbol, exchanges)
        if price_df is None or price_df.empty:
            return False
        
        # Convert to Heikin-Ashi (Required for your CipherB indicator)
        ha_data = heikin_ashi(price_df)
        
        # Calculate CipherB signals (Your validated private indicator)
        signals = detect_cipherb_signals(ha_data, config['cipherb'])
        if signals.empty:
            return False
        
        # Calculate Stochastic RSI for confirmation
        stoch_rsi = calculate_stoch_rsi(
            price_df['Close'],
            rsi_period=config['stoch_rsi']['rsi_period'],
            stoch_period=config['stoch_rsi']['stoch_period'],
            k_smooth=config['stoch_rsi']['k_smooth'],
            d_smooth=config['stoch_rsi']['d_smooth']
        )
        
        # Get latest values (most recent completed candle)
        latest_signals = signals.iloc[-1]
        latest_stoch_rsi = stoch_rsi.iloc[-1] if not stoch_rsi.empty else 50
        
        # Check BUY signals (CipherB + StochRSI confirmation)
        if latest_signals['buySignal']:
            if check_stoch_rsi_confirmation(stoch_rsi, 'buy', config['stoch_rsi']['oversold_threshold']):
                if deduplicator.is_alert_allowed(symbol, 'BUY'):
                    print(f"🟢 BUY SIGNAL: {symbol} - wt1:{latest_signals['wt1']:.1f}, wt2:{latest_signals['wt2']:.1f}, StochRSI:{latest_stoch_rsi:.0f}")
                    send_telegram_alert(
                        coin_data, 'BUY',
                        latest_signals['wt1'], latest_signals['wt2'], latest_stoch_rsi
                    )
                    alert_sent = True
        
        # Check SELL signals (CipherB + StochRSI confirmation)
        if latest_signals['sellSignal']:
            if check_stoch_rsi_confirmation(stoch_rsi, 'sell', config['stoch_rsi']['overbought_threshold']):
                if deduplicator.is_alert_allowed(symbol, 'SELL'):
                    print(f"🔴 SELL SIGNAL: {symbol} - wt1:{latest_signals['wt1']:.1f}, wt2:{latest_signals['wt2']:.1f}, StochRSI:{latest_stoch_rsi:.0f}")
                    send_telegram_alert(
                        coin_data, 'SELL',
                        latest_signals['wt1'], latest_signals['wt2'], latest_stoch_rsi
                    )
                    alert_sent = True
    
    except Exception as e:
        print(f"❌ Error processing {symbol}: {e}")
    
    return alert_sent

def process_coins_in_batches(coins, deduplicator, exchanges, config, batch_size=25):
    """Process coins in batches to manage resources"""
    total_alerts = 0
    total_processed = 0
    
    print(f"📊 Processing {len(coins)} coins in batches of {batch_size}...")
    
    for i in range(0, len(coins), batch_size):
        batch = coins[i:i+batch_size]
        batch_alerts = 0
        
        print(f"🔄 Batch {i//batch_size + 1}: Scanning coins {i+1}-{min(i+batch_size, len(coins))}")
        
        for coin in batch:
            if process_coin_signals(coin, deduplicator, exchanges, config):
                batch_alerts += 1
            total_processed += 1
            
            # Rate limiting between requests
            time.sleep(0.3)
        
        total_alerts += batch_alerts
        print(f"✅ Batch complete: {batch_alerts} alerts from {len(batch)} coins")
        
        # Small delay between batches
        if i + batch_size < len(coins):
            time.sleep(1)
    
    print(f"📈 TOTAL SUMMARY: {total_alerts} alerts from {total_processed} coins")
    return total_alerts > 0

def main():
    """Main CipherB signal detection process"""
    print(f"🚀 Starting CipherB signal detection at {datetime.now().strftime('%Y-%m-%d %H:%M:%S IST')}")
    
    # Load configuration
    config = load_config()
    
    # Load cached coin data (175 coins)
    coins = load_cached_coins()
    
    if not coins:
        print("❌ No coin data available")
        return
    
    # Initialize exchanges
    exchanges = initialize_exchanges()
    if not exchanges:
        print("❌ No exchanges available")
        return
    
    print(f"📊 Available exchanges: {[name for name, _ in exchanges]}")
    print(f"📊 Market scan: {len(coins)} qualifying coins (100M+ cap, 30M+ volume)")
    
    # Initialize deduplicator with 2-hour cooldown
    deduplicator = AlertDeduplicator(cooldown_hours=config['alerts']['cooldown_hours'])
    
    # Process all coins in batches
    batch_size = config['alerts']['batch_size']
    any_alert = process_coins_in_batches(coins, deduplicator, exchanges, config, batch_size)
    
    # Final status
    if not any_alert:
        print("ℹ️ No CipherB signals detected in this scan")
    
    # Cleanup expired cache entries
    deduplicator.cleanup_expired_entries()
    
    print("✅ CipherB signal detection completed")
    print(f"⏰ Next scan: {(datetime.now() + timedelta(minutes=10)).strftime('%H:%M:%S IST')}")

if __name__ == '__main__':
    main()
