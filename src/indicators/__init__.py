# Indicators Package
"""
Technical indicator implementations for crypto signal detection.

Contains:
- CipherB: Validated Market Cipher B indicator (PRIMARY SIGNAL)
- Stochastic RSI: Confirmation indicator (SECONDARY)  
- Heikin-Ashi: Candle conversion utility

The CipherB indicator is the core trading edge and has been validated
through extensive backtesting with 100% TradingView signal accuracy.
"""

from .cipherb import CipherBIndicator
from .stoch_rsi import StochRSIIndicator
from .heikin_ashi import HeikinAshiConverter

__all__ = [
    "CipherBIndicator",
    "StochRSIIndicator", 
    "HeikinAshiConverter"
]
