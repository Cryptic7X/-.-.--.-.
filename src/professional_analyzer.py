#!/usr/bin/env python3
"""
Professional CipherB 4H Analysis Engine
High-performance 4-hour timeframe analysis with your validated indicator
"""

#!/usr/bin/env python3
"""
Professional CipherB 4H Analysis Engine with New Candle Boundary Detection
High-performance 4-hour timeframe analysis with duplicate signal prevention
"""

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
from alerts.professional_telegram import send_professional_alert

class ProfessionalAnalyzer:
    def __init__(self):
        self.config = self.load_configuration()
        self.exchanges = self.initialize_professional_exchanges()
        self.deduplicator = AlertDeduplicator(cooldown_hours=self.config['alerts']['cooldown_hours'])
        
    def load_configuration(self):
        """Load professional system configuration"""
        config_path = os.path.join(os.path.dirname(__file__), '..', 'config', 'config.yaml')
        with open(config_path, 'r') as f:
            return yaml.safe_load(f)
    
    def load_professional_market_data(self):
        """Load professionally filtered market data"""
        cache_file = os.path.join(os.path.dirname(__file__), '..', 'cache', 'professional_market_data.json')
        
        if not os.path.exists(cache_file):
            print("❌ Professional market data not found. Run market scan first.")
            return None
        
        with open(cache_file, 'r') as f:
            data = json.load(f)
        
        coins = data.get('coins', [])
        metadata = data.get('metadata', {})
        
        print(f"📊 Loaded {len(coins)} professionally filtered coins")
        print(f"🕐 Last updated: {metadata.get('last_updated', 'Unknown')}")
        
        return coins
    
    def initialize_professional_exchanges(self):
        """Initialize professional-grade exchange connections"""
        exchanges = []
        
        # BingX (Primary - Professional Grade)
        try:
            bingx_config = {
                'apiKey': os.getenv('BINGX_API_KEY', ''),
                'secret': os.getenv('BINGX_SECRET_KEY', ''),
                'sandbox': False,
                'rateLimit': 300,  # Conservative for 4H
                'enableRateLimit': True,
                'timeout': self.config['exchanges']['timeout'] * 1000,
            }
            
            bingx = ccxt.bingx(bingx_config)
            exchanges.append(('BingX-Pro', bingx))
            
        except Exception as e:
            print(f"⚠️ BingX Professional initialization failed: {e}")
        
        # KuCoin (Professional Fallback)
        try:
            kucoin_config = {
                'rateLimit': 1000,
                'enableRateLimit': True,
                'timeout': self.config['exchanges']['timeout'] * 1000,
            }
            
            kucoin = ccxt.kucoin(kucoin_config)
            exchanges.append(('KuCoin-Pro', kucoin))
            
        except Exception as e:
            print(f"⚠️ KuCoin Professional initialization failed: {e}")
        
        return exchanges
    
    def is_new_4h_candle(self, signal_timestamp):
        """
        Check if this signal is from a NEW 4H candle (prevents duplicate alerts)
        Only allows alerts within first 15 minutes of new 4H candle opening
        """
        current_time = datetime.now()
        
        # Calculate current 4H boundary (00:00, 04:00, 08:00, 12:00, 16:00, 20:00)
        current_4h_start = current_time.replace(minute=0, second=0, microsecond=0)
        current_4h_start = current_4h_start.replace(hour=(current_4h_start.hour // 4) * 4)
        
        # Calculate how long ago the current 4H candle started
        time_since_4h_open = current_time - current_4h_start
        
        # Convert signal timestamp to timezone-naive for comparison
        if signal_timestamp.tzinfo is not None:
            signal_timestamp = signal_timestamp.replace(tzinfo=None)
        
        # Calculate when the signal's 4H candle started
        signal_4h_start = signal_timestamp.replace(minute=0, second=0, microsecond=0)
        signal_4h_start = signal_4h_start.replace(hour=(signal_4h_start.hour // 4) * 4)
        
        # Check if signal is from current 4H candle AND within first 15 minutes
        is_current_candle = signal_4h_start == current_4h_start
        is_fresh_signal = time_since_4h_open <= timedelta(minutes=15)
        
        if not is_current_candle:
            print(f"   ⏰ Signal from old 4H candle: {signal_4h_start} vs current: {current_4h_start}")
            return False
        
        if not is_fresh_signal:
            print(f"   ⏰ Signal not fresh: {time_since_4h_open.total_seconds()/60:.1f}min since 4H open")
            return False
        
        print(f"   ✅ Fresh 4H signal: {time_since_4h_open.total_seconds()/60:.1f}min since candle open")
        return True
    
    def fetch_professional_4h_data(self, symbol):
        """Fetch high-quality 4H OHLCV data with professional validation"""
        candles_required = self.config['scan']['candles_required']
        
        for exchange_name, exchange in self.exchanges:
            try:
                # Fetch 4H candles (CRITICAL: This is the timeframe change)
                ohlcv = exchange.fetch_ohlcv(f"{symbol}/USDT", '4h', limit=candles_required)
                
                if len(ohlcv) < 50:  # Need sufficient 4H data for analysis
                    continue
                
                # Convert to professional DataFrame
                df = pd.DataFrame(ohlcv, columns=['timestamp', 'Open', 'High', 'Low', 'Close', 'Volume'])
                df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
                df.set_index('timestamp', inplace=True)
                
                # CRITICAL: Adjust timezone to IST (UTC+5:30) for TradingView alignment
                df.index = df.index + pd.Timedelta(hours=5, minutes=30)
                
                # Professional data validation
                if self.validate_4h_data_quality(df, symbol):
                    return df, exchange_name
                
            except Exception as e:
                continue
        
        return None, None
    
    def validate_4h_data_quality(self, df, symbol):
        """Professional 4H data quality validation"""
        if df.empty or len(df) < 30:
            return False
        
        # Check for reasonable price ranges
        if df['Close'].iloc[-1] <= 0 or df['Volume'].iloc[-1] <= 0:
            return False
        
        # Check for sufficient price movement (not completely flat)
        price_range = df['High'].max() - df['Low'].min()
        if price_range / df['Close'].mean() < 0.01:  # Less than 1% range
            return False
        
        return True
    
    def analyze_coin_professionally(self, coin_data):
        """Professional 4H analysis with NEW CANDLE BOUNDARY CHECK"""
        symbol = coin_data.get('symbol', '').upper()
        
        try:
            # Fetch professional 4H data
            price_df, exchange_used = self.fetch_professional_4h_data(symbol)
            if price_df is None:
                return False, f"No 4H data available"
            
            # Convert to Heikin-Ashi (Required for your CipherB)
            ha_data = heikin_ashi(price_df)
            
            # Apply your validated CipherB indicator (4H timeframe)
            cipherb_signals = detect_cipherb_signals(ha_data, self.config['cipherb'])
            if cipherb_signals.empty:
                return False, "No CipherB signals"
            
            # Calculate StochRSI confirmation (4H timeframe)
            stoch_rsi = calculate_stoch_rsi(
                price_df['Close'],
                rsi_period=self.config['stoch_rsi']['rsi_period'],
                stoch_period=self.config['stoch_rsi']['stoch_period'],
                k_smooth=self.config['stoch_rsi']['k_smooth'],
                d_smooth=self.config['stoch_rsi']['d_smooth']
            )
            
            # Get latest 4H signal data
            latest_signals = cipherb_signals.iloc[-1]
            latest_stoch_rsi = stoch_rsi.iloc[-1] if not stoch_rsi.empty else 50
            latest_timestamp = cipherb_signals.index[-1]
            
            # 🔑 KEY FIX: Check if this is a NEW 4H candle signal
            if not self.is_new_4h_candle(latest_timestamp):
                return False, "Signal not from new 4H candle"
            
            signal_sent = False
            
            # Professional BUY signal processing
            if latest_signals['buySignal']:
                if check_stoch_rsi_confirmation(stoch_rsi, 'buy', self.config['stoch_rsi']['oversold_threshold']):
                    if self.deduplicator.is_alert_allowed(symbol, 'BUY'):
                        print(f"🟢 PROFESSIONAL BUY: {symbol} (4H) - Exchange: {exchange_used}")
                        print(f"   📊 CipherB: wt1={latest_signals['wt1']:.1f}, wt2={latest_signals['wt2']:.1f}")
                        print(f"   ⚡ StochRSI: {latest_stoch_rsi:.0f}")
                        print(f"   🕐 Timestamp: {latest_timestamp}")
                        
                        send_professional_alert(
                            coin_data, 'BUY',
                            latest_signals['wt1'], latest_signals['wt2'], latest_stoch_rsi,
                            exchange_used, latest_timestamp
                        )
                        signal_sent = True
            
            # Professional SELL signal processing
            if latest_signals['sellSignal']:
                if check_stoch_rsi_confirmation(stoch_rsi, 'sell', self.config['stoch_rsi']['overbought_threshold']):
                    if self.deduplicator.is_alert_allowed(symbol, 'SELL'):
                        print(f"🔴 PROFESSIONAL SELL: {symbol} (4H) - Exchange: {exchange_used}")
                        print(f"   📊 CipherB: wt1={latest_signals['wt1']:.1f}, wt2={latest_signals['wt2']:.1f}")
                        print(f"   ⚡ StochRSI: {latest_stoch_rsi:.0f}")
                        print(f"   🕐 Timestamp: {latest_timestamp}")
                        
                        send_professional_alert(
                            coin_data, 'SELL',
                            latest_signals['wt1'], latest_signals['wt2'], latest_stoch_rsi,
                            exchange_used, latest_timestamp
                        )
                        signal_sent = True
            
            return signal_sent, f"Analysis complete - {exchange_used}"
            
        except Exception as e:
            return False, f"Analysis error: {str(e)[:100]}"
    
    def run_professional_analysis(self):
        """Execute professional 4H market analysis with duplicate prevention"""
        print(f"\n" + "="*80)
        print("🚀 PROFESSIONAL CIPHERB 4H ANALYSIS STARTING")
        print("="*80)
        print(f"🕐 Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S IST')}")
        print(f"⏱️ Timeframe: {self.config['system']['timeframe'].upper()}")
        print(f"🎯 System: {self.config['system']['name']}")
        print(f"🔄 New Candle Detection: Active (15min window)")
        
        # Load professional market data
        coins = self.load_professional_market_data()
        if not coins:
            return
        
        print(f"📊 Available exchanges: {[name for name, _ in self.exchanges]}")
        print(f"📈 Coins to analyze: {len(coins)}")
        
        # Professional batch processing
        batch_size = self.config['alerts']['batch_size']
        total_signals = 0
        total_analyzed = 0
        
        for i in range(0, len(coins), batch_size):
            batch = coins[i:i+batch_size]
            batch_signals = 0
            
            print(f"\n🔄 Professional Batch {i//batch_size + 1}: Analyzing coins {i+1}-{min(i+batch_size, len(coins))}")
            
            for coin in batch:
                signal_sent, status = self.analyze_coin_professionally(coin)
                if signal_sent:
                    batch_signals += 1
                total_analyzed += 1
                
                # Professional rate limiting
                time.sleep(self.config['exchanges']['rate_limit'])
            
            total_signals += batch_signals
            print(f"✅ Batch complete: {batch_signals} signals from {len(batch)} coins")
            
            # Inter-batch delay
            if i + batch_size < len(coins):
                time.sleep(2)
        
        # Professional summary
        print(f"\n" + "="*80)
        print("📊 PROFESSIONAL ANALYSIS COMPLETE")
        print("="*80)
        print(f"🎯 Total coins analyzed: {total_analyzed}")
        print(f"🚨 Professional signals sent: {total_signals}")
        print(f"📈 Signal efficiency: {total_signals/total_analyzed*100:.2f}%")
        print(f"⏰ Next analysis: {(datetime.now() + timedelta(minutes=10)).strftime('%H:%M:%S IST')}")
        print("="*80)
        
        # Cleanup
        self.deduplicator.cleanup_expired_entries()

def main():
    analyzer = ProfessionalAnalyzer()
    analyzer.run_professional_analysis()

if __name__ == '__main__':
    main()

