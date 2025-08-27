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

import os
import json
from datetime import datetime, timedelta

class AlertDeduplicator:
    def __init__(self, cooldown_hours=2):
        self.cooldown_hours = cooldown_hours
        self.cache_file = 'cache/alert_cache.json'
        self.cache = self._load_cache()
    
    def _load_cache(self):
        """Load alert cache from file"""
        if os.path.exists(self.cache_file):
            try:
                with open(self.cache_file, 'r') as f:
                    return json.load(f)
            except (json.JSONDecodeError, FileNotFoundError):
                pass
        return {}
    
    def _save_cache(self):
        """Save alert cache to file"""
        os.makedirs(os.path.dirname(self.cache_file), exist_ok=True)
        with open(self.cache_file, 'w') as f:
            json.dump(self.cache, f, indent=2)
    
    def is_alert_allowed(self, symbol, signal_type):
        """
        Check if alert is allowed based on cooldown period
        Returns True if alert should be sent, False if still in cooldown
        """
        key = f"{symbol.upper()}_{signal_type.upper()}"
        current_time = datetime.utcnow()
        
        if key in self.cache:
            last_alert_time = datetime.fromisoformat(self.cache[key])
            time_diff = current_time - last_alert_time
            
            if time_diff < timedelta(hours=self.cooldown_hours):
                # Still in cooldown period
                return False
        
        # Update cache with current time
        self.cache[key] = current_time.isoformat()
        self._save_cache()
        
        return True
    
    def cleanup_expired_entries(self):
        """Remove expired entries from cache"""
        current_time = datetime.utcnow()
        expired_keys = []
        
        for key, timestamp_str in self.cache.items():
            try:
                timestamp = datetime.fromisoformat(timestamp_str)
                if current_time - timestamp > timedelta(hours=self.cooldown_hours * 2):
                    expired_keys.append(key)
            except ValueError:
                expired_keys.append(key)
        
        for key in expired_keys:
            del self.cache[key]
        
        if expired_keys:
            self._save_cache()
