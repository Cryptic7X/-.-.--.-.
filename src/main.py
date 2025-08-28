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
        return None, None
    
    with open(cache_file, 'r') as f:
        data = json.load(f)
    
    return data.get('standard', []), data.get('high_risk', [])

def initialize_exchanges():
    """Initialize exchanges with India-friendly options"""
    exchanges = []
    
    # BingX (Primary - works in India)
    try:
        bingx = ccxt.bingx({
            'rateLimit': 100,
            'enableRateLimit': True,
        })
        exchanges.append(('BingX', bingx))
    except Exception as e:
        print(f"⚠️ BingX initialization failed: {e}")
    
    # KuCoin (Fallback - works in India)
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
    """Fetch FRESH 1-hour OHLCV data with proper IST timezone"""
    for exchange_name, exchange in exchanges:
        try:
            print(f"📊 Fetching {symbol} data from {exchange_name}...")
            
            # Fetch last 100 candles for better accuracy
            ohlcv = exchange.fetch_ohlcv(f"{symbol}/USDT", '1h', limit=100)
            
            if len(ohlcv) < 50:
                continue
            
            df = pd.DataFrame(ohlcv, columns=['timestamp', 'Open', 'High', 'Low', 'Close', 'Volume'])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            df.set_index('timestamp', inplace=True)
            
            # Convert to IST (UTC+5:30) - MATCH your TradingView timezone
            df.index = df.index + pd.Timedelta(hours=5, minutes=30)
            
            # Ensure we have the most recent candle
            latest_candle_time = df.index[-1]
            current_time = datetime.now()
            
            print(f"✅ Latest candle: {latest_candle_time}, Current: {current_time}")
            return df
            
        except Exception as e:
            print(f"❌ {exchange_name} failed for {symbol}: {e}")
            continue
    
    return None

def process_coin_signals(coin_data, channel_type, deduplicator, exchanges, config):
    """Process coin signals with REAL-TIME validation"""
    symbol = coin_data.get('symbol', '').upper()
    alert_sent = False

    try:
        # Fetch FRESH price data
        price_df = fetch_price_data(symbol, exchanges)
        if price_df is None or price_df.empty:
            return False

        # Convert to Heikin-Ashi
        ha_data = heikin_ashi(price_df)
        
        # Calculate CipherB signals on FRESH data
        signals = detect_cipherb_signals(ha_data, config['cipherb'])
        if signals.empty:
            return False

        # Calculate Stochastic RSI confirmation
        stoch_rsi = calculate_stoch_rsi(
            price_df['Close'],
            rsi_period=config['stoch_rsi']['rsi_period'],
            stoch_period=config['stoch_rsi']['stoch_period'],
            k_smooth=config['stoch_rsi']['k_smooth'],
            d_smooth=config['stoch_rsi']['d_smooth']
        )

        # Get CURRENT signal (last few candles)
        latest_signals = signals.iloc[-1]
        latest_stoch_rsi = stoch_rsi.iloc[-1] if not stoch_rsi.empty else 50

        # Check for BUY signals
        if latest_signals['buySignal']:
            if check_stoch_rsi_confirmation(stoch_rsi, 'buy', config['stoch_rsi']['oversold_threshold']):
                if deduplicator.is_alert_allowed(symbol, 'BUY'):
                    print(f"🟢 BUY SIGNAL DETECTED: {symbol} at {datetime.now().strftime('%H:%M:%S IST')}")
                    send_telegram_alert(
                        coin_data, 'BUY', channel_type,
                        latest_signals['wt1'], latest_signals['wt2'], latest_stoch_rsi
                    )
                    alert_sent = True

        # Check for SELL signals
        if latest_signals['sellSignal']:
            if check_stoch_rsi_confirmation(stoch_rsi, 'sell', config['stoch_rsi']['overbought_threshold']):
                if deduplicator.is_alert_allowed(symbol, 'SELL'):
                    print(f"🔴 SELL SIGNAL DETECTED: {symbol} at {datetime.now().strftime('%H:%M:%S IST')}")
                    send_telegram_alert(
                        coin_data, 'SELL', channel_type,
                        latest_signals['wt1'], latest_signals['wt2'], latest_stoch_rsi
                    )
                    alert_sent = True

    except Exception as e:
        print(f"❌ Error processing {symbol}: {e}")

    return alert_sent

def main():
    """Main signal detection process"""
    print(f"🚀 Starting CipherB signal detection at {datetime.now().strftime('%Y-%m-%d %H:%M:%S IST')}")
    
    config = load_config()
    standard_coins, high_risk_coins = load_cached_coins()
    
    if not standard_coins and not high_risk_coins:
        print("❌ No coin data available")
        return
    
    exchanges = initialize_exchanges()
    if not exchanges:
        print("❌ No exchanges available")
        return
    
    print(f"📊 Exchanges: {[name for name, _ in exchanges]}")
    print(f"📊 Available: {len(standard_coins)} standard, {len(high_risk_coins)} high-risk coins")
    
    deduplicator = AlertDeduplicator(cooldown_hours=config['alerts']['cooldown_hours'])
    
    any_alert = False
    processed_standard = 0
    processed_high_risk = 0

    # Process ALL standard coins (remove limit)
    print("🔍 Scanning ALL STANDARD coins...")
    for i, coin in enumerate(standard_coins):
        if i > 0:
            time.sleep(0.2)  # Rate limiting
        if process_coin_signals(coin, 'standard', deduplicator, exchanges, config):
            any_alert = True
        processed_standard += 1

    # Process ALL high-risk coins (remove limit)  
    print("🔍 Scanning ALL HIGH-RISK coins...")
    for i, coin in enumerate(high_risk_coins):
        if i > 0:
            time.sleep(0.2)  # Rate limiting
        if process_coin_signals(coin, 'high_risk', deduplicator, exchanges, config):
            any_alert = True
        processed_high_risk += 1

    print(f"📊 Processed: {processed_standard} standard + {processed_high_risk} high-risk coins")

    if not any_alert:
        print("ℹ️ No signals detected in this run.")

    deduplicator.cleanup_expired_entries()
    print("✅ CipherB signal detection completed")
    print(f"⏰ Next scan: {(datetime.now() + timedelta(minutes=10)).strftime('%H:%M:%S IST')}")

if __name__ == '__main__':
    main()
