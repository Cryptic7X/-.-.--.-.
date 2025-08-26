# Alerts Package
"""
Alert system components for Telegram notifications and deduplication.

Contains:
- TelegramAlert: Enhanced message formatting with TradingView links
- AlertDeduplicator: 2-hour cooldown system to prevent spam alerts

The alert system sends rich, formatted messages to separate Telegram
channels for standard and high-risk signals.
"""

from .telegram_handler import TelegramAlert
from .deduplication import AlertDeduplicator

__all__ = [
    "TelegramAlert",
    "AlertDeduplicator"
]
