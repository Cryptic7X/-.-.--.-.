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
from datetime import datetime, timedelta

class AlertDeduplicator:
    def __init__(self, cooldown_hours=3):
        self.cooldown_hours = cooldown_hours
        self.cache_file = os.path.join(os.path.dirname(__file__), '..', '..', 'cache', 'alert_cache.json')
        self.cache = self.load_persistent_cache()
    
    def load_persistent_cache(self):
        """Load cache from file to persist between runs"""
        try:
            with open(self.cache_file, 'r') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return {}
    
    def save_persistent_cache(self):
        """Save cache to file"""
        os.makedirs(os.path.dirname(self.cache_file), exist_ok=True)
        with open(self.cache_file, 'w') as f:
            json.dump(self.cache, f, indent=2)
    
    def get_market_candle_start(self, signal_timestamp):
        # Ensure UTC
        if signal_timestamp.tzinfo:
            utc_ts = signal_timestamp.tz_convert('UTC')
        else:
            utc_ts = signal_timestamp
    
        # Floor to nearest 2-hour UTC boundary (00:00,02:00,...)
        boundary_hour = (utc_ts.hour // 2) * 2
        candle_start_utc = utc_ts.replace(hour=boundary_hour, minute=0, second=0, microsecond=0)
    
        # Convert back to IST
        candle_start_ist = candle_start_utc + timedelta(hours=5, minutes=30)
        return candle_start_ist

    
    def is_alert_allowed(self, symbol, signal_type, signal_timestamp):
        # Calculate 2H candle start (market-aligned)
        if signal_timestamp.tzinfo is not None:
            signal_timestamp = signal_timestamp.replace(tzinfo=None)
        
        # Round to 2H boundary: 00:00, 02:00, 04:00, etc.
        candle_hour = (signal_timestamp.hour // 2) * 2
        candle_start = signal_timestamp.replace(hour=candle_hour, minute=0, second=0, microsecond=0)
        
        # Create unique key per 2H candle
        key = f"{symbol}_{signal_type}_{candle_start.strftime('%Y%m%d_%H%M')}"
        
        if key in self.cache:
            print(f"   🚫 Already alerted: {symbol} {signal_type} at {candle_start}")
            return False
        
        self.cache[key] = datetime.utcnow().isoformat()
        self.save_persistent_cache()
        return True

    
    def cleanup_expired_entries(self):
        """Remove expired entries (older than 7 days)"""
        current_time = datetime.utcnow()
        expired_keys = []
        
        for key, timestamp_str in self.cache.items():
            try:
                last_alert = datetime.fromisoformat(timestamp_str)
                if current_time - last_alert > timedelta(days=7):
                    expired_keys.append(key)
            except ValueError:
                expired_keys.append(key)  # Remove invalid entries
        
        for key in expired_keys:
            del self.cache[key]
        
        if expired_keys:
            self.save_persistent_cache()
            print(f"🧹 Cleaned up {len(expired_keys)} expired cache entries")
