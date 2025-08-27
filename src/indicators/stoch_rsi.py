"""
Stochastic RSI Indicator
========================

Stochastic RSI confirmation indicator for CipherB signals.
Used as secondary confirmation for overbought/oversold conditions.

Standard Parameters:
- RSI Period: 14
- Stochastic Period: 14  
- %K Period: 3
- %D Period: 3
- Oversold Level: ≤ 20
- Overbought Level: ≥ 80
"""

import pandas as pd
import numpy as np

def rsi(series, period=14):
    """Calculate RSI"""
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

def stochastic(high, low, close, k_period=14):
    """Calculate Stochastic %K"""
    lowest_low = low.rolling(window=k_period).min()
    highest_high = high.rolling(window=k_period).max()
    k_percent = 100 * (close - lowest_low) / (highest_high - lowest_low)
    return k_percent

def calculate_stoch_rsi(close_data, rsi_period=14, stoch_period=14, k_smooth=3, d_smooth=3):
    """
    Calculate Stochastic RSI
    Standard parameters: (14, 14, 3, 3)
    """
    if len(close_data) < max(rsi_period, stoch_period) + k_smooth + d_smooth:
        return pd.Series(index=close_data.index, dtype=float)
    
    # Calculate RSI
    rsi_values = rsi(close_data, rsi_period)
    
    # Apply Stochastic to RSI
    stoch_rsi = stochastic(rsi_values, rsi_values, rsi_values, stoch_period)
    
    # Smooth with SMA
    k_line = stoch_rsi.rolling(window=k_smooth).mean()
    d_line = k_line.rolling(window=d_smooth).mean()
    
    return k_line

def check_stoch_rsi_confirmation(stoch_rsi_values, signal_type):
    """
    Check Stochastic RSI confirmation for buy/sell signals
    Buy: StochRSI <= 20 (oversold)
    Sell: StochRSI >= 80 (overbought)
    """
    if stoch_rsi_values.empty:
        return False
    
    current_value = stoch_rsi_values.iloc[-1]
    
    if signal_type.lower() == 'buy':
        return current_value <= 20
    elif signal_type.lower() == 'sell':
        return current_value >= 80
    
    return False

