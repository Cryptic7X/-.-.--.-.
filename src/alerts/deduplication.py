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
        """
        Calculate market-aligned 2H candle start
        Market candles: 05:30, 07:30, 09:30, 11:30, etc. IST
        """
        # Convert to timezone-naive if needed
        if signal_timestamp.tzinfo is not None:
            signal_timestamp = signal_timestamp.replace(tzinfo=None)
        
        # Start from 05:30 IST base
        base_hour = 5
        base_minute = 30
        
        # Calculate which 2H period this timestamp falls into
        minutes_from_base = (signal_timestamp.hour - base_hour) * 60 + (signal_timestamp.minute - base_minute)
        if minutes_from_base < 0:
            # Handle times before 05:30 (previous day)
            minutes_from_base += 24 * 60
        
        # Find the 2H period (120 minutes each)
        period_index = minutes_from_base // 120
        
        # Calculate the candle start time
        candle_start_minutes = base_hour * 60 + base_minute + (period_index * 120)
        candle_start_hour = (candle_start_minutes // 60) % 24
        candle_start_minute = candle_start_minutes % 60
        
        candle_start = signal_timestamp.replace(
            hour=candle_start_hour,
            minute=candle_start_minute,
            second=0,
            microsecond=0
        )
        
        return candle_start
    
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
