#!/usr/bin/env python3
"""
Dual Confirmation Trading System
- CipherB exact signals on 15m timeframe  
- StochRSI %D confirmation on 3h timeframe
- Fresh signals only (within 2-minute window)
- Enhanced Telegram alerts with confirmation details
"""

import os
import sys
import time
import json
import ccxt
import pandas as pd
import yaml
from datetime import datetime, timedelta

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from alerts.telegram_dual import send_dual_confirmation_alert
from alerts.deduplication_fresh import FreshSignalDeduplicator
from indicators.cipherb_exact import detect_exact_cipherb_signals
from indicators.stochrsi_3h import calculate_stochastic_rsi, check_stochrsi_confirmation

def get_ist_time():
    """Convert UTC to IST"""
    return datetime.utcnow() + timedelta(hours=5, minutes=30)

class DualConfirmationAnalyzer:
    def __init__(self):
        self.config = self.load_config()
        self.deduplicator = FreshSignalDeduplicator(freshness_minutes=2)
        self.exchanges = self.init_exchanges()
        self.market_data = self.load_market_data()

    def load_config(self):
        config_path = os.path.join(os.path.dirname(__file__), '..', '..', 'config', 'config.yaml')
        with open(config_path, 'r') as f:
            return yaml.safe_load(f)

    def load_market_data(self):
        cache_file = os.path.join(os.path.dirname(__file__), '..', '..', 'cache', 'high_risk_market_data.json')
        
        if not os.path.exists(cache_file):
            print("❌ Market data cache not found")
            return []
        
        with open(cache_file, 'r') as f:
            data = json.load(f)
        
        return data.get('coins', [])

    def init_exchanges(self):
        exchanges = []
        
        try:
            bingx = ccxt.bingx({
                'apiKey': os.getenv('BINGX_API_KEY', ''),
                'secret': os.getenv('BINGX_SECRET_KEY', ''),
                'rateLimit': 300,
                'enableRateLimit': True,
                'timeout': 30000,
            })
            exchanges.append(('BingX', bingx))
            print("✅ BingX exchange initialized")
        except Exception as e:
            print(f"⚠️ BingX initialization failed: {e}")
        
        try:
            kucoin = ccxt.kucoin({
                'rateLimit': 500,
                'enableRateLimit': True,
                'timeout': 30000,
            })
            exchanges.append(('KuCoin', kucoin))
            print("✅ KuCoin exchange initialized")
        except Exception as e:
            print(f"⚠️ KuCoin initialization failed: {e}")
        
        return exchanges

    def fetch_ohlcv_data(self, symbol, timeframe, limit=200):
        """Fetch OHLCV data from exchanges"""
        for exchange_name, exchange in self.exchanges:
            try:
                ohlcv = exchange.fetch_ohlcv(f"{symbol}/USDT", timeframe, limit=limit)
                
                if len(ohlcv) < 50:
                    continue
                
                df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
                df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
                df.set_index('timestamp', inplace=True)
                
                if len(df) > 30 and df['close'].iloc[-1] > 0:
                    return df, exchange_name
                
            except Exception as e:
                print(f"⚠️ {symbol} {timeframe} data failed on {exchange_name}: {str(e)[:50]}")
                continue
        
        return None, None

    def analyze_coin_dual_confirmation(self, coin_data):
        """
        Analyze coin with dual confirmation: CipherB + StochRSI
        """
        symbol = coin_data.get('symbol', '').upper()
        
        try:
            # Step 1: Fetch 15m data for CipherB
            print(f"🔍 Analyzing {symbol}")
            price_df_15m, exchange_15m = self.fetch_ohlcv_data(symbol, '15m', 200)
            if price_df_15m is None:
                print(f"❌ {symbol}: No 15m data available")
                return None
            
            # Keep UTC timestamps for freshness checking
            price_df_15m['utc_timestamp'] = price_df_15m.index
            # Convert to IST for display
            price_df_15m.index = price_df_15m.index + pd.Timedelta(hours=5, minutes=30)
            
            # Step 2: Apply CipherB detection
            signals_df = detect_exact_cipherb_signals(price_df_15m, self.config['cipherb'])
            if signals_df.empty:
                return None
            
            # Step 3: Check latest signal freshness
            latest_signal = signals_df.iloc[-1]
            signal_timestamp_utc = price_df_15m['utc_timestamp'].iloc[-1]
            signal_timestamp_ist = signals_df.index[-1]
            
            current_time = datetime.utcnow()
            time_since_signal = current_time - signal_timestamp_utc.to_pydatetime()
            
            print(f"   CipherB signal age: {time_since_signal.total_seconds():.0f}s")
            print(f"   BUY: {latest_signal['buySignal']} | SELL: {latest_signal['sellSignal']}")
            
            # Determine signal type
            signal_type = None
            if latest_signal['buySignal']:
                signal_type = 'BUY'
            elif latest_signal['sellSignal']:
                signal_type = 'SELL'
            else:
                return None
            
            # Step 4: Check deduplication
            if not self.deduplicator.is_signal_fresh_and_new(symbol, signal_type, signal_timestamp_utc):
                return None
            
            # Step 5: Fetch 3h data for StochRSI
            price_df_3h, exchange_3h = self.fetch_ohlcv_data(symbol, '3h', 100)
            stochrsi_confirmed = False
            stochrsi_d_value = None
            stochrsi_status = "unavailable"
            
            if price_df_3h is not None:
                try:
                    # Calculate StochRSI
                    k_line, d_line = calculate_stochastic_rsi(price_df_3h['close'])
                    
                    # Check confirmation using %D line
                    stochrsi_confirmed, stochrsi_d_value = check_stochrsi_confirmation(
                        d_line, signal_type, oversold=30, overbought=70
                    )
                    
                    if stochrsi_confirmed:
                        stochrsi_status = "confirmed"
                        print(f"   ✅ StochRSI CONFIRMED: {signal_type} with D={stochrsi_d_value:.1f}")
                    else:
                        stochrsi_status = "rejected"
                        print(f"   ❌ StochRSI REJECTED: {signal_type} with D={stochrsi_d_value:.1f}")
                        return None  # Reject if StochRSI doesn't confirm
                        
                except Exception as e:
                    print(f"   ⚠️ StochRSI calculation failed: {str(e)[:50]}")
                    stochrsi_status = "calc_error"
            
            # Handle fallback behavior
            if stochrsi_status == "unavailable":
                print(f"   ⚠️ StochRSI unavailable - proceeding with CipherB only")
            elif stochrsi_status == "rejected":
                return None  # Already handled above
            elif stochrsi_status == "calc_error":
                print(f"   ⚠️ StochRSI error - proceeding with CipherB only")
            
            # Step 6: Create final signal
            return {
                'symbol': symbol,
                'signal_type': signal_type,
                'wt1': latest_signal['wt1'],
                'wt2': latest_signal['wt2'],
                'price': coin_data.get('current_price', 0),
                'change_24h': coin_data.get('price_change_percentage_24h', 0),
                'market_cap': coin_data.get('market_cap', 0),
                'exchange': exchange_15m,
                'timestamp': signal_timestamp_ist,
                'signal_age_seconds': time_since_signal.total_seconds(),
                'stochrsi_status': stochrsi_status,
                'stochrsi_d_value': stochrsi_d_value,
                'coin_data': coin_data
            }
            
        except Exception as e:
            print(f"❌ {symbol} analysis failed: {str(e)[:100]}")
            return None

    def run_dual_confirmation_analysis(self):
        """
        Run complete dual confirmation analysis
        """
        ist_current = get_ist_time()
        
        print("="*80)
        print("🎯 DUAL CONFIRMATION ANALYSIS")
        print("="*80)
        print(f"🕐 Analysis Time: {ist_current.strftime('%Y-%m-%d %H:%M:%S IST')}")
        print(f"📊 CipherB 15m + StochRSI 3h confirmation system")
        print(f"⚡ Fresh signals only (within 2 minutes)")
        print(f"🔍 Coins to analyze: {len(self.market_data)}")
        print("="*80)
        
        if not self.market_data:
            print("❌ No market data available")
            return
        
        # Cleanup old signals
        self.deduplicator.cleanup_old_signals()
        
        # Process coins
        confirmed_signals = []
        batch_size = 12  # Reduced for dual timeframe fetching
        total_analyzed = 0
        
        for i in range(0, len(self.market_data), batch_size):
            batch = self.market_data[i:i + batch_size]
            batch_num = i // batch_size + 1
            total_batches = (len(self.market_data) - 1) // batch_size + 1
            
            print(f"\n🔄 Processing batch {batch_num}/{total_batches}")
            
            for coin in batch:
                signal_result = self.analyze_coin_dual_confirmation(coin)
                if signal_result:
                    confirmed_signals.append(signal_result)
                    status = signal_result['stochrsi_status']
                    d_val = signal_result['stochrsi_d_value']
                    
                    if status == "confirmed":
                        print(f"🚨 {signal_result['signal_type']}: {signal_result['symbol']} | D={d_val:.1f} ✅")
                    else:
                        print(f"🚨 {signal_result['signal_type']}: {signal_result['symbol']} | {status} ⚠️")
                
                total_analyzed += 1
                time.sleep(0.5)  # Rate limiting for dual timeframe fetching
        
        # Send alerts
        if confirmed_signals:
            success = send_dual_confirmation_alert(confirmed_signals)
            if success:
                confirmed_count = len([s for s in confirmed_signals if s['stochrsi_status'] == 'confirmed'])
                fallback_count = len(confirmed_signals) - confirmed_count
                
                print(f"\n✅ DUAL CONFIRMATION ALERT SENT")
                print(f"   Total signals: {len(confirmed_signals)}")
                print(f"   StochRSI confirmed: {confirmed_count}")
                print(f"   CipherB fallback: {fallback_count}")
            else:
                print(f"\n❌ Failed to send alert")
        else:
            print(f"\n📊 No confirmed signals detected")
        
        print(f"\n" + "="*80)
        print("🎯 DUAL CONFIRMATION ANALYSIS COMPLETE")
        print("="*80)
        print(f"📊 Total analyzed: {total_analyzed}")
        print(f"🚨 Confirmed signals: {len(confirmed_signals)}")
        print(f"📱 Alert sent: {'Yes' if confirmed_signals else 'No'}")
        print("="*80)

if __name__ == '__main__':
    analyzer = DualConfirmationAnalyzer()
    analyzer.run_dual_confirmation_analysis()
