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

import sys
import os
import time
import pandas as pd
from datetime import datetime, timedelta
import json
import traceback

# Add src to path for imports
sys.path.append(os.path.join(os.path.dirname(__file__)))

from data_fetcher import DataFetcher
from filters import MarketFilter
from indicators.cipherb import CipherBIndicator
from indicators.stoch_rsi import StochRSIIndicator  
from indicators.heikin_ashi import HeikinAshiConverter
from alerts.telegram_handler import TelegramAlert
from alerts.deduplication import AlertDeduplicator
from utils.symbol_validator import SymbolValidator


class CryptoAlertSystem:
    """
    Main Crypto Alert System Controller
    
    Orchestrates the complete signal detection and alerting workflow:
    1. Fetch and filter market data
    2. Generate CipherB signals  
    3. Confirm with Stochastic RSI
    4. Check deduplication rules
    5. Send Telegram alerts
    """
    
    def __init__(self, config_path='config/config.yaml'):
        """
        Initialize the complete alert system
        
        Args:
            config_path: Path to configuration file
        """
        
        print("🚀 Initializing Crypto Alert System...")
        
        # Initialize all components
        self.data_fetcher = DataFetcher(config_path)
        self.market_filter = MarketFilter(config_path)
        self.cipher_indicator = CipherBIndicator()
        self.stoch_rsi = StochRSIIndicator()
        self.ha_converter = HeikinAshiConverter()
        self.telegram_alert = TelegramAlert(config_path)
        self.deduplicator = AlertDeduplicator(config_path)
        self.symbol_validator = SymbolValidator(config_path)
        
        # System statistics
        self.stats = {
            'start_time': datetime.now(),
            'coins_processed': 0,
            'signals_detected': 0,
            'alerts_sent': 0,
            'errors': 0
        }
        
        print("✅ System initialized successfully")
    
    def run_daily_market_scan(self, force_refresh=False):
        """
        Run daily market data collection and filtering
        This should run once per day to refresh the coin lists
        
        Args:
            force_refresh: Force fresh data fetch
            
        Returns:
            dict: Filtered coin lists
        """
        
        print("\n📊 Starting daily market scan...")
        
        try:
            # Fetch comprehensive market data (6 pages = 1,500 coins)
            market_data = self.data_fetcher.fetch_comprehensive_market_data(force_refresh)
            
            if not market_data:
                raise Exception("No market data received from CoinGecko")
            
            # Apply market filters
            filtered_coins = self.market_filter.filter_coins(market_data)
            
            # Cache filtered results
            self._cache_filtered_coins(filtered_coins)
            
            # Display summary
            print(f"✅ Daily scan complete:")
            print(f"   📈 Standard coins: {len(filtered_coins['standard'])}")  
            print(f"   ⚡ High-risk coins: {len(filtered_coins['high_risk'])}")
            print(f"   📊 Total coins processed: {len(market_data)}")
            
            return filtered_coins
            
        except Exception as e:
            print(f"❌ Daily scan error: {str(e)}")
            self.stats['errors'] += 1
            
            # Try to load cached data as fallback
            return self._load_cached_coins()
    
    def run_signal_detection(self):
        """
        Run 10-minute signal detection cycle
        This is the main trading signal detection loop
        
        Returns:
            dict: Detection results and statistics
        """
        
        print(f"\n🔍 Starting signal detection at {datetime.now().strftime('%H:%M:%S IST')}")
        
        try:
            # Load cached coin lists
            filtered_coins = self._load_cached_coins()
            
            if not filtered_coins or (not filtered_coins['standard'] and not filtered_coins['high_risk']):
                print("⚠️  No filtered coins available. Running daily scan...")
                filtered_coins = self.run_daily_market_scan()
            
            # Process both standard and high-risk coins
            results = {
                'standard': self._process_coin_category(filtered_coins['standard'], 'standard'),
                'high_risk': self._process_coin_category(filtered_coins['high_risk'], 'high_risk')
            }
            
            # Update system statistics
            total_processed = len(filtered_coins['standard']) + len(filtered_coins['high_risk'])
            total_signals = results['standard']['signals_found'] + results['high_risk']['signals_found']
            total_alerts = results['standard']['alerts_sent'] + results['high_risk']['alerts_sent']
            
            self.stats['coins_processed'] += total_processed
            self.stats['signals_detected'] += total_signals
            self.stats['alerts_sent'] += total_alerts
            
            print(f"✅ Signal detection complete:")
            print(f"   🪙 Coins processed: {total_processed}")
            print(f"   📶 Signals found: {total_signals}")
            print(f"   📢 Alerts sent: {total_alerts}")
            
            return results
            
        except Exception as e:
            print(f"❌ Signal detection error: {str(e)}")
            self.stats['errors'] += 1
            traceback.print_exc()
            return {'error': str(e)}
    
    def _process_coin_category(self, coin_list, category):
        """
        Process a category of coins (standard or high-risk)
        
        Args:
            coin_list: List of coins to process
            category: 'standard' or 'high_risk'
            
        Returns:
            dict: Processing results
        """
        
        if not coin_list:
            return {'coins_processed': 0, 'signals_found': 0, 'alerts_sent': 0}
        
        signals_found = 0
        alerts_sent = 0
        errors = 0
        
        print(f"   🔄 Processing {len(coin_list)} {category} coins...")
        
        for coin in coin_list:
            try:
                result = self._process_single_coin(coin, category)
                
                if result['signal_detected']:
                    signals_found += 1
                    
                if result['alert_sent']:
                    alerts_sent += 1
                    
            except Exception as e:
                errors += 1
                print(f"     ❌ Error processing {coin.get('symbol', 'UNKNOWN')}: {str(e)}")
                continue
        
        return {
            'coins_processed': len(coin_list),
            'signals_found': signals_found,
            'alerts_sent': alerts_sent,
            'errors': errors
        }
    
    def _process_single_coin(self, coin_data, category):
        """
        Process a single coin for signal detection
        
        Args:
            coin_data: Individual coin market data
            category: 'standard' or 'high_risk'
            
        Returns:
            dict: Processing result
        """
        
        symbol = coin_data.get('symbol', '').upper()
        trading_symbol = f"{symbol}/USDT"
        
        result = {
            'symbol': symbol,
            'signal_detected': False,
            'alert_sent': False,
            'signal_type': None,
            'reason': None
        }
        
        try:
            # Fetch OHLCV data
            ohlcv_data = self.data_fetcher.fetch_ohlcv_data(trading_symbol, '1h', 50)
            
            if ohlcv_data is None or len(ohlcv_data) < 30:
                result['reason'] = 'Insufficient OHLCV data'
                return result
            
            # Convert to Heikin-Ashi
            ha_data = self.ha_converter.convert(ohlcv_data)
            
            # Calculate CipherB signals (PRIMARY SIGNAL)
            cipher_signals = self.cipher_indicator.calculate_signals(ha_data)
            
            if cipher_signals is None:
                result['reason'] = 'CipherB calculation failed'
                return result
            
            # Check for latest CipherB signal
            latest_cipher = cipher_signals.iloc[-1]
            
            if latest_cipher['buySignal']:
                signal_type = 'BUY'
            elif latest_cipher['sellSignal']:
                signal_type = 'SELL'
            else:
                result['reason'] = 'No CipherB signal'
                return result
            
            # STOCHASTIC RSI CONFIRMATION (SECONDARY)
            stoch_rsi_data = self.stoch_rsi.calculate(ohlcv_data)
            
            if stoch_rsi_data is None:
                result['reason'] = 'Stochastic RSI calculation failed'
                return result
            
            latest_stoch = stoch_rsi_data.iloc[-1]
            
            # Confirmation logic
            confirmed = False
            
            if signal_type == 'BUY' and latest_stoch['stoch_rsi_k'] <= 20:
                confirmed = True
            elif signal_type == 'SELL' and latest_stoch['stoch_rsi_k'] >= 80:
                confirmed = True
            
            if not confirmed:
                result['reason'] = f'Stochastic RSI confirmation failed (value: {latest_stoch["stoch_rsi_k"]:.1f})'
                return result
            
            # Signal detected!
            result['signal_detected'] = True
            result['signal_type'] = signal_type
            
            # CHECK DEDUPLICATION
            if self.deduplicator.is_duplicate(symbol, signal_type):
                result['reason'] = 'Signal in cooldown period'
                return result
            
            # SEND ALERT
            alert_data = {
                'symbol': symbol,
                'signal_type': signal_type,
                'category': category,
                'price': coin_data.get('current_price', 0),
                'change_24h': coin_data.get('price_change_percentage_24h', 0),
                'market_cap': coin_data.get('market_cap', 0),
                'volume': coin_data.get('total_volume', 0),
                'wt1': latest_cipher['wt1'],
                'wt2': latest_cipher['wt2'],
                'stoch_rsi': latest_stoch['stoch_rsi_k']
            }
            
            # Generate TradingView link
            tv_link = self.symbol_validator.get_tradingview_link(symbol)
            alert_data['tv_link'] = tv_link
            
            # Send Telegram alert
            success = self.telegram_alert.send_signal_alert(alert_data)
            
            if success:
                # Record in deduplication cache
                self.deduplicator.record_alert(symbol, signal_type)
                result['alert_sent'] = True
                
                print(f"     ✅ Alert sent: {symbol} {signal_type} ({category})")
            else:
                result['reason'] = 'Telegram alert failed'
            
            return result
            
        except Exception as e:
            result['reason'] = f'Processing error: {str(e)}'
            return result
    
    def _cache_filtered_coins(self, filtered_coins):
        """Cache filtered coin data"""
        try:
            cache_file = 'cache/filtered_coins.json'
            with open(cache_file, 'w') as f:
                json.dump(filtered_coins, f)
        except Exception as e:
            print(f"Cache write error: {e}")
    
    def _load_cached_coins(self):
        """Load cached filtered coin data"""
        try:
            cache_file = 'cache/filtered_coins.json'
            if os.path.exists(cache_file):
                with open(cache_file, 'r') as f:
                    return json.load(f)
        except Exception as e:
            print(f"Cache read error: {e}")
        
        return {'standard': [], 'high_risk': []}
    
    def get_system_status(self):
        """Get comprehensive system status"""
        
        runtime = datetime.now() - self.stats['start_time']
        
        return {
            'status': 'operational',
            'uptime': str(runtime),
            'statistics': self.stats.copy(),
            'cache_stats': self.data_fetcher.get_cache_stats(),
            'filter_criteria': self.market_filter.get_criteria_summary(),
            'deduplication_stats': self.deduplicator.get_stats()
        }


def main():
    """
    Main entry point for the system
    Can be called with different modes:
    - daily_scan: Run daily market data collection
    - signal_detection: Run 10-minute signal detection
    - status: Show system status
    """
    
    if len(sys.argv) < 2:
        print("Usage: python main.py [daily_scan|signal_detection|status]")
        return
    
    mode = sys.argv[1].lower()
    
    try:
        # Initialize system
        system = CryptoAlertSystem('../config/config.yaml')
        
        if mode == 'daily_scan':
            system.run_daily_market_scan()
            
        elif mode == 'signal_detection':
            system.run_signal_detection()
            
        elif mode == 'status':
            status = system.get_system_status()
            print(json.dumps(status, indent=2, default=str))
            
        else:
            print(f"Unknown mode: {mode}")
            print("Available modes: daily_scan, signal_detection, status")
    
    except KeyboardInterrupt:
        print("\n🛑 System stopped by user")
    
    except Exception as e:
        print(f"\n💥 System error: {str(e)}")
        traceback.print_exc()


if __name__ == "__main__":
    main()
