"""
Stochastic RSI 3h Confirmation Module
Calculates StochRSI %D on 3h timeframe for signal confirmation
"""

import pandas as pd
import numpy as np

def calculate_rsi(close_prices, period=14):
    """Calculate RSI using standard formula"""
    delta = close_prices.diff()
    gains = delta.where(delta > 0, 0)
    losses = -delta.where(delta < 0, 0)
    
    avg_gain = gains.ewm(com=period-1, adjust=False).mean()
    avg_loss = losses.ewm(com=period-1, adjust=False).mean()
    
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    
    return rsi

def calculate_stochastic_rsi(close_prices, rsi_period=14, stoch_period=14, smooth_k=3, smooth_d=3):
    """
    Calculate Stochastic RSI with default parameters
    Returns %K and %D lines
    """
    # Calculate RSI first
    rsi = calculate_rsi(close_prices, rsi_period)
    
    # Apply Stochastic formula to RSI
    min_rsi = rsi.rolling(window=stoch_period).min()
    max_rsi = rsi.rolling(window=stoch_period).max()
    
    # Avoid division by zero
    rsi_range = max_rsi - min_rsi
    stoch_rsi = np.where(rsi_range != 0, (rsi - min_rsi) / rsi_range, 0)
    stoch_rsi = pd.Series(stoch_rsi, index=rsi.index)
    
    # Calculate %K and %D lines
    k_line = stoch_rsi.rolling(window=smooth_k).mean() * 100
    d_line = k_line.rolling(window=smooth_d).mean()
    
    return k_line, d_line

def check_stochrsi_confirmation(d_line, signal_type, oversold=30, overbought=70):
    """
    Check StochRSI %D confirmation based on signal type
    Using %D line as it's slower and more reliable than %K
    """
    if d_line.empty or pd.isna(d_line.iloc[-1]):
        return False, None
        
    latest_d = d_line.iloc[-1]
    
    if signal_type == 'BUY':
        # %D must be in oversold zone (≤30)
        confirmed = latest_d <= oversold
        return confirmed, latest_d
    elif signal_type == 'SELL':
        # %D must be in overbought zone (≥70) 
        confirmed = latest_d >= overbought
        return confirmed, latest_d
    
    return False, latest_d
