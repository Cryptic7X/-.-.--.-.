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
    """
    Calculate RSI manually without TA-Lib dependency
    """
    if len(series) < period + 1:
        return pd.Series(index=series.index, dtype=float)
    
    delta = series.diff()
    gain = delta.where(delta > 0, 0)
    loss = -delta.where(delta < 0, 0)
    
    # Calculate initial averages
    avg_gain = gain.rolling(window=period).mean()
    avg_loss = loss.rolling(window=period).mean()
    
    # Calculate RSI
    rs = avg_gain / avg_loss
    rsi_values = 100 - (100 / (1 + rs))
    
    return rsi_values

def stochastic(high, low, close, k_period=14):
    """
    Calculate Stochastic %K manually
    """
    if len(close) < k_period:
        return pd.Series(index=close.index, dtype=float)
    
    lowest_low = low.rolling(window=k_period).min()
    highest_high = high.rolling(window=k_period).max()
    
    # Avoid division by zero
    denominator = highest_high - lowest_low
    k_percent = np.where(denominator != 0, 
                        100 * (close - lowest_low) / denominator, 
                        50)
    
    return pd.Series(k_percent, index=close.index)

def calculate_stoch_rsi(close_data, rsi_period=14, stoch_period=14, k_smooth=3, d_smooth=3):
    """
    Calculate Stochastic RSI without TA-Lib dependency
    Standard parameters: (14, 14, 3, 3)
    """
    if len(close_data) < max(rsi_period, stoch_period) + k_smooth + d_smooth:
        return pd.Series(index=close_data.index, dtype=float)
    
    # Calculate RSI
    rsi_values = rsi(close_data, rsi_period)
    
    # Apply Stochastic to RSI (using RSI as high, low, and close)
    stoch_rsi = stochastic(rsi_values, rsi_values, rsi_values, stoch_period)
    
    # Smooth with SMA
    k_line = pd.Series(stoch_rsi).rolling(window=k_smooth).mean()
    
    return k_line

def check_stoch_rsi_confirmation(stoch_rsi_values, signal_type):
    """
    Check Stochastic RSI confirmation for buy/sell signals
    Buy: StochRSI <= 20 (oversold)
    Sell: StochRSI >= 80 (overbought)
    """
    if stoch_rsi_values.empty or pd.isna(stoch_rsi_values.iloc[-1]):
        return False
    
    current_value = stoch_rsi_values.iloc[-1]
    
    if signal_type.lower() == 'buy':
        return current_value <= 20
    elif signal_type.lower() == 'sell':
        return current_value >= 80
    
    return False
