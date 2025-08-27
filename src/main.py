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
import ccxt
import pandas as pd
from datetime import datetime, timedelta

# Add current directory to Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

# Import local modules
from utils.heikin_ashi import heikin_ashi
from indicators.cipherb_fixed import detect_cipherb_signals
from indicators.stoch_rsi import calculate_stoch_rsi, check_stoch_rsi_confirmation
from alerts.deduplication import AlertDeduplicator
from alerts.telegram_handler import send_telegram_alert

def load_cached_coins():
    """Load cached coin data from daily scan"""
    cache_file = os.path.join(os.path.dirname(__file__), '..', 'cache', 'daily_coin_data.json')
    
    if not os.path.exists(cache_file):
        print("❌ No cached coin data found. Run daily scan first.")
        return None, None
    
    with open(cache_file, 'r') as f:
        data = json.load(f)
    
    return data.get('standard', []), data.get('high_risk', [])

def fetch_price_data(symbol):
    """Fetch 1-hour OHLCV data using CCXT"""
    try:
        exchanges_to_try = [
            ccxt.binance({'rateLimit': 1200}),
            ccxt.bybit({'rateLimit': 1200})
        ]
        
        for exchange in exchanges_to_try:
            try:
                ohlcv = exchange.fetch_ohlcv(f"{symbol}/USDT", '1h', limit=50)
                
                if len(ohlcv) < 20:
                    continue
                
                df = pd.DataFrame(ohlcv, columns=['timestamp', 'Open', 'High', 'Low', 'Close', 'Volume'])
                df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
                df.set_index('timestamp', inplace=True)
                
                # Adjust timezone to IST (UTC+5:30)
                df.index = df.index + pd.Timedelta(hours=5, minutes=30)
                
                return df
                
            except Exception:
                continue
        
        return None
        
    except Exception as e:
        print(f"❌ Error fetching data for {symbol}: {e}")
        return None

def process_coin_signals(coin_data, channel_type, deduplicator):
    """Process a single coin for signals"""
    symbol = coin_data.get('symbol', '').upper()
    
    try:
        price_df = fetch_price_data(symbol)
        if price_df is None or price_df.empty:
            return
        
        ha_data = heikin_ashi(price_df)
        signals = detect_cipherb_signals(ha_data)
        if signals.empty:
            return
        
        stoch_rsi = calculate_stoch_rsi(price_df['Close'])
        latest_signals = signals.iloc[-1]
        latest_stoch_rsi = stoch_rsi.iloc[-1] if not stoch_rsi.empty else 50
        
        if latest_signals['buySignal']:
            if check_stoch_rsi_confirmation(stoch_rsi, 'buy'):
                if deduplicator.is_alert_allowed(symbol, 'BUY'):
                    send_telegram_alert(
                        coin_data, 'BUY', channel_type,
                        latest_signals['wt1'], latest_signals['wt2'], latest_stoch_rsi
                    )
        
        if latest_signals['sellSignal']:
            if check_stoch_rsi_confirmation(stoch_rsi, 'sell'):
                if deduplicator.is_alert_allowed(symbol, 'SELL'):
                    send_telegram_alert(
                        coin_data, 'SELL', channel_type,
                        latest_signals['wt1'], latest_signals['wt2'], latest_stoch_rsi
                    )
    
    except Exception as e:
        print(f"❌ Error processing {symbol}: {e}")

def main():
    """Main signal detection process"""
    print(f"🚀 Starting signal detection at {datetime.now().strftime('%Y-%m-%d %H:%M:%S IST')}")
    
    standard_coins, high_risk_coins = load_cached_coins()
    
    if not standard_coins and not high_risk_coins:
        print("❌ No coin data available")
        return
    
    print(f"📊 Processing {len(standard_coins)} standard and {len(high_risk_coins)} high-risk coins")
    
    deduplicator = AlertDeduplicator(cooldown_hours=2)
    
    for coin in standard_coins[:5]:  # Process first 5 coins only for testing
        process_coin_signals(coin, 'standard', deduplicator)
    
    for coin in high_risk_coins[:5]:  # Process first 5 coins only for testing
        process_coin_signals(coin, 'high_risk', deduplicator)
    
    deduplicator.cleanup_expired_entries()
    print("✅ Signal detection completed")

if __name__ == '__main__':
    main()
