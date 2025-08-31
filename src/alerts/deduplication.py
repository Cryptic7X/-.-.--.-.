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
        try:
            with open(self.cache_file, 'r') as f:
                cache = json.load(f)
            print(f"📁 Loaded cache with {len(cache)} entries")
            return cache
        except (FileNotFoundError, json.JSONDecodeError):
            print("📁 No existing cache found, starting fresh")
            return {}

    
    def save_persistent_cache(self):
        """Save cache to file"""
        os.makedirs(os.path.dirname(self.cache_file), exist_ok=True)
        with open(self.cache_file, 'w') as f:
            json.dump(self.cache, f, indent=2)
    
    def get_market_candle_start(self, signal_timestamp):
        """
        Calculate market-aligned 2H candle start for IST boundaries
        IST 2H candles: 03:30-05:30, 05:30-07:30, 07:30-09:30, etc.
        """
        # Convert to timezone-naive datetime if needed
        if hasattr(signal_timestamp, 'tzinfo') and signal_timestamp.tzinfo is not None:
            # Already in IST, convert to naive
            ts = signal_timestamp.replace(tzinfo=None)
        else:
            ts = signal_timestamp
        
        # IST 2H candles start at 03:30, 05:30, 07:30, 09:30, etc.
        # Find which 2H period this timestamp belongs to
        hour = ts.hour
        minute = ts.minute
        
        # Convert to minutes since midnight
        total_minutes = hour * 60 + minute
        
        # IST 2H boundaries in minutes: 210 (03:30), 330 (05:30), 450 (07:30), etc.
        # Each period is 120 minutes
        # First boundary is at 03:30 = 210 minutes
        
        if total_minutes < 210:  # Before 03:30, belongs to previous day's 01:30-03:30
            candle_start_minutes = 90  # 01:30
            ts = ts - timedelta(days=1) if total_minutes >= 90 else ts
        else:
            # Find which 2H period (starting from 03:30)
            minutes_from_0330 = total_minutes - 210  # Minutes since 03:30
            period_index = minutes_from_0330 // 120  # Which 2H period
            candle_start_minutes = 210 + (period_index * 120)  # Start of this period
        
        # Convert back to hour:minute
        candle_hour = candle_start_minutes // 60
        candle_minute = candle_start_minutes % 60
        
        # Create candle start timestamp
        candle_start = ts.replace(
            hour=candle_hour % 24,
            minute=candle_minute,
            second=0,
            microsecond=0
        )
        
        print(f"🕐 Signal at {ts.strftime('%H:%M')} → Candle start: {candle_start.strftime('%H:%M')}")
        return candle_start


    
    def is_alert_allowed(self, symbol, signal_type, signal_timestamp):
        candle_start = self.get_market_candle_start(signal_timestamp)
        key = f"{symbol}_{signal_type}_{candle_start.strftime('%Y%m%d_%H%M')}"
        
        # DEBUG: Print what's happening
        print(f"🔍 DEBUG: {symbol} {signal_type}")
        print(f"   Signal timestamp: {signal_timestamp}")
        print(f"   Calculated candle start: {candle_start}")
        print(f"   Cache key: {key}")
        print(f"   Key exists in cache: {key in self.cache}")
        
        if key in self.cache:
            print(f"   ❌ BLOCKED - Already sent at: {self.cache[key]}")
            return False
        
        self.cache[key] = datetime.utcnow().isoformat()
        self.save_persistent_cache()
        print(f"   ✅ ALLOWED - First time for this candle")
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
