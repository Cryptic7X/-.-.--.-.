"""
Alert Deduplication System
==========================

Prevents duplicate alerts for the same coin and signal type within a cooldown period.
Uses in-memory storage for simplicity (no external Redis required).

Features:
- 2-hour cooldown between identical signals
- Fresh validation after cooldown expires  
- Persistent storage across system restarts
- Statistics tracking
"""

import json
import os
import time
from datetime import datetime, timedelta
import yaml


class AlertDeduplicator:
    """
    Alert Deduplication Manager
    
    Prevents spam alerts by tracking recent signals and enforcing cooldown periods.
    """
    
    def __init__(self, config_path='../config/config.yaml'):
        """
        Initialize alert deduplicator
        
        Args:
            config_path: Path to configuration file
        """
        
        self.config = self._load_config(config_path)
        self.cache_file = 'cache/alert_cache.json'
        
        # Cooldown settings from config
        self.cooldown_hours = self.config.get('alerts', {}).get('cooldown_hours', 2)
        self.cooldown_seconds = self.cooldown_hours * 3600
        
        # Load existing cache
        self.alert_cache = self._load_cache()
        
        # Statistics
        self.stats = {
            'alerts_recorded': 0,
            'duplicates_blocked': 0,
            'cache_cleanups': 0
        }
    
    def _load_config(self, config_path):
        """Load configuration from YAML file"""
        try:
            with open(config_path, 'r') as f:
                return yaml.safe_load(f)
        except Exception as e:
            print(f"Config loading error: {e}")
            return {}
    
    def _load_cache(self):
        """Load alert cache from file"""
        if os.path.exists(self.cache_file):
            try:
                with open(self.cache_file, 'r') as f:
                    cache_data = json.load(f)
                    
                # Clean expired entries on load
                current_time = time.time()
                cleaned_cache = {
                    key: timestamp for key, timestamp in cache_data.items()
                    if current_time - timestamp < self.cooldown_seconds
                }
                
                if len(cleaned_cache) < len(cache_data):
                    print(f"Cleaned {len(cache_data) - len(cleaned_cache)} expired cache entries")
                
                return cleaned_cache
                
            except Exception as e:
                print(f"Cache loading error: {e}")
        
        return {}
    
    def _save_cache(self):
        """Save alert cache to file"""
        try:
            # Ensure cache directory exists
            os.makedirs(os.path.dirname(self.cache_file), exist_ok=True)
            
            with open(self.cache_file, 'w') as f:
                json.dump(self.alert_cache, f)
                
        except Exception as e:
            print(f"Cache saving error: {e}")
    
    def _get_cache_key(self, symbol, signal_type):
        """Generate cache key for symbol and signal type"""
        return f"{symbol.upper()}_{signal_type.upper()}"
    
    def is_duplicate(self, symbol, signal_type):
        """
        Check if alert would be a duplicate
        
        Args:
            symbol: Coin symbol (e.g., 'BTC')
            signal_type: 'BUY' or 'SELL'
            
        Returns:
            bool: True if duplicate (in cooldown period)
        """
        
        cache_key = self._get_cache_key(symbol, signal_type)
        current_time = time.time()
        
        if cache_key in self.alert_cache:
            last_alert_time = self.alert_cache[cache_key]
            time_elapsed = current_time - last_alert_time
            
            if time_elapsed < self.cooldown_seconds:
                # Still in cooldown period
                self.stats['duplicates_blocked'] += 1
                return True
            else:
                # Cooldown expired, remove from cache
                del self.alert_cache[cache_key]
        
        return False
    
    def record_alert(self, symbol, signal_type):
        """
        Record an alert in the cache
        
        Args:
            symbol: Coin symbol
            signal_type: Signal type
        """
        
        cache_key = self._get_cache_key(symbol, signal_type)
        current_time = time.time()
        
        self.alert_cache[cache_key] = current_time
        self.stats['alerts_recorded'] += 1
        
        # Save to file
        self._save_cache()
        
        print(f"   📝 Alert recorded: {symbol} {signal_type} (cooldown until {datetime.fromtimestamp(current_time + self.cooldown_seconds).strftime('%H:%M:%S')})")
    
    def cleanup_expired(self):
        """
        Clean up expired entries from cache
        
        Returns:
            int: Number of entries cleaned
        """
        
        current_time = time.time()
        initial_count = len(self.alert_cache)
        
        # Remove expired entries
        expired_keys = [
            key for key, timestamp in self.alert_cache.items()
            if current_time - timestamp >= self.cooldown_seconds
        ]
        
        for key in expired_keys:
            del self.alert_cache[key]
        
        cleaned_count = len(expired_keys)
        
        if cleaned_count > 0:
            self.stats['cache_cleanups'] += 1
            self._save_cache()
            print(f"Cleaned {cleaned_count} expired cache entries")
        
        return cleaned_count
    
    def get_active_cooldowns(self):
        """
        Get list of active cooldowns
        
        Returns:
            list: Active cooldowns with remaining time
        """
        
        current_time = time.time()
        active_cooldowns = []
        
        for cache_key, alert_time in self.alert_cache.items():
            remaining_seconds = (alert_time + self.cooldown_seconds) - current_time
            
            if remaining_seconds > 0:
                symbol, signal_type = cache_key.split('_', 1)
                remaining_minutes = remaining_seconds / 60
                
                active_cooldowns.append({
                    'symbol': symbol,
                    'signal_type': signal_type,
                    'remaining_minutes': remaining_minutes,
                    'expires_at': datetime.fromtimestamp(alert_time + self.cooldown_seconds).strftime('%H:%M:%S')
                })
        
        # Sort by remaining time
        active_cooldowns.sort(key=lambda x: x['remaining_minutes'])
        
        return active_cooldowns
    
    def force_reset_cooldown(self, symbol, signal_type):
        """
        Force reset cooldown for specific symbol and signal
        
        Args:
            symbol: Coin symbol
            signal_type: Signal type
            
        Returns:
            bool: True if cooldown was reset
        """
        
        cache_key = self._get_cache_key(symbol, signal_type)
        
        if cache_key in self.alert_cache:
            del self.alert_cache[cache_key]
            self._save_cache()
            print(f"Reset cooldown for {symbol} {signal_type}")
            return True
        
        return False
    
    def reset_all_cooldowns(self):
        """
        Reset all active cooldowns (emergency use)
        
        Returns:
            int: Number of cooldowns reset
        """
        
        reset_count = len(self.alert_cache)
        self.alert_cache.clear()
        self._save_cache()
        
        print(f"Reset all cooldowns ({reset_count} entries)")
        return reset_count
    
    def get_cooldown_info(self, symbol, signal_type):
        """
        Get cooldown information for specific symbol and signal
        
        Args:
            symbol: Coin symbol
            signal_type: Signal type
            
        Returns:
            dict: Cooldown information or None
        """
        
        cache_key = self._get_cache_key(symbol, signal_type)
        
        if cache_key in self.alert_cache:
            alert_time = self.alert_cache[cache_key]
            current_time = time.time()
            remaining_seconds = (alert_time + self.cooldown_seconds) - current_time
            
            if remaining_seconds > 0:
                return {
                    'in_cooldown': True,
                    'alert_time': datetime.fromtimestamp(alert_time).strftime('%Y-%m-%d %H:%M:%S'),
                    'remaining_seconds': remaining_seconds,
                    'remaining_minutes': remaining_seconds / 60,
                    'expires_at': datetime.fromtimestamp(alert_time + self.cooldown_seconds).strftime('%Y-%m-%d %H:%M:%S')
                }
            else:
                # Expired, clean up
                del self.alert_cache[cache_key]
                self._save_cache()
        
        return {'in_cooldown': False}
    
    def get_stats(self):
        """Get deduplication statistics"""
        return {
            **self.stats,
            'active_cooldowns': len(self.alert_cache),
            'cooldown_hours': self.cooldown_hours,
            'cache_file_exists': os.path.exists(self.cache_file)
        }
    
    def get_cache_summary(self):
        """Get summary of cache contents"""
        
        if not self.alert_cache:
            return "Cache is empty"
        
        active_cooldowns = self.get_active_cooldowns()
        
        summary = f"Active cooldowns ({len(active_cooldowns)}):\n"
        
        for cooldown in active_cooldowns[:10]:  # Show first 10
            summary += f"  • {cooldown['symbol']} {cooldown['signal_type']}: {cooldown['remaining_minutes']:.0f}m remaining\n"
        
        if len(active_cooldowns) > 10:
            summary += f"  ... and {len(active_cooldowns) - 10} more"
        
        return summary


# Test/debug functions
def test_deduplicator():
    """Test the deduplication system"""
    
    dedup = AlertDeduplicator()
    
    print("=== Alert Deduplication Test ===")
    
    # Test 1: First alert (should not be duplicate)
    print("\nTest 1: First BTC BUY alert")
    is_dup = dedup.is_duplicate('BTC', 'BUY')
    print(f"Is duplicate: {is_dup}")
    
    if not is_dup:
        dedup.record_alert('BTC', 'BUY')
    
    # Test 2: Immediate duplicate (should be blocked)
    print("\nTest 2: Immediate duplicate BTC BUY alert")
    is_dup = dedup.is_duplicate('BTC', 'BUY')
    print(f"Is duplicate: {is_dup}")
    
    # Test 3: Different signal type (should not be duplicate)
    print("\nTest 3: BTC SELL alert (different type)")
    is_dup = dedup.is_duplicate('BTC', 'SELL')
    print(f"Is duplicate: {is_dup}")
    
    # Show active cooldowns
    print("\n=== Active Cooldowns ===")
    cooldowns = dedup.get_active_cooldowns()
    for cooldown in cooldowns:
        print(f"{cooldown['symbol']} {cooldown['signal_type']}: {cooldown['remaining_minutes']:.1f}m remaining")
    
    # Show statistics
    print(f"\n=== Statistics ===")
    stats = dedup.get_stats()
    for key, value in stats.items():
        print(f"{key}: {value}")


if __name__ == "__main__":
    test_deduplicator()
