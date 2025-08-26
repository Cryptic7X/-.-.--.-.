"""
Heikin-Ashi Candle Conversion
============================

Converts regular OHLC candles to Heikin-Ashi format.
Used as input for CipherB indicator calculations.

Heikin-Ashi candles smooth price action and reduce noise,
making them ideal for trend analysis and signal generation.
"""

import pandas as pd
import numpy as np


def heikin_ashi(df):
    """
    Convert regular OHLC candles to Heikin-Ashi format
    
    Heikin-Ashi Calculation:
    - HA Close = (Open + High + Low + Close) / 4
    - HA Open = (Previous HA Open + Previous HA Close) / 2  
    - HA High = max(HA Open, HA Close, High)
    - HA Low = min(HA Open, HA Close, Low)
    
    Args:
        df: DataFrame with columns ['Open', 'High', 'Low', 'Close'] and datetime index
        
    Returns:
        DataFrame: Heikin-Ashi candles with same structure as input
    """
    
    if df is None or df.empty:
        raise ValueError("Input DataFrame is empty")
        
    # Validate required columns
    required_cols = ['Open', 'High', 'Low', 'Close']
    if not all(col in df.columns for col in required_cols):
        raise ValueError(f"Missing required columns. Need: {required_cols}")
    
    # Create Heikin-Ashi DataFrame with same index
    ha_df = pd.DataFrame(index=df.index)
    
    # HA Close = (O + H + L + C) / 4
    ha_df['Close'] = (df['Open'] + df['High'] + df['Low'] + df['Close']) / 4
    
    # Initialize HA Open column
    ha_df['Open'] = 0.0
    
    # First HA Open = (First O + First C) / 2
    ha_df.iloc[0, ha_df.columns.get_loc('Open')] = (
        df.iloc[0]['Open'] + df.iloc[0]['Close']
    ) / 2
    
    # Calculate subsequent HA Open values
    # HA Open = (Previous HA Open + Previous HA Close) / 2
    for i in range(1, len(ha_df)):
        ha_df.iloc[i, ha_df.columns.get_loc('Open')] = (
            ha_df.iloc[i-1]['Open'] + ha_df.iloc[i-1]['Close']
        ) / 2
    
    # HA High = max(HA Open, HA Close, Original High)
    ha_df['High'] = pd.concat([
        ha_df['Open'], 
        ha_df['Close'], 
        df['High']
    ], axis=1).max(axis=1)
    
    # HA Low = min(HA Open, HA Close, Original Low)
    ha_df['Low'] = pd.concat([
        ha_df['Open'], 
        ha_df['Close'], 
        df['Low']
    ], axis=1).min(axis=1)
    
    # Add volume if present in original data
    if 'Volume' in df.columns:
        ha_df['Volume'] = df['Volume']
    
    return ha_df


def validate_heikin_ashi(ha_df):
    """
    Validate Heikin-Ashi candles for correctness
    
    Args:
        ha_df: DataFrame with Heikin-Ashi data
        
    Returns:
        bool: True if valid, raises ValueError if invalid
    """
    
    if ha_df is None or ha_df.empty:
        raise ValueError("Heikin-Ashi DataFrame is empty")
    
    # Check for required columns
    required_cols = ['Open', 'High', 'Low', 'Close']
    if not all(col in ha_df.columns for col in required_cols):
        raise ValueError(f"Missing required columns: {required_cols}")
    
    # Check for valid OHLC relationships
    # High should be >= max(Open, Close)
    invalid_high = ha_df[ha_df['High'] < ha_df[['Open', 'Close']].max(axis=1)]
    if not invalid_high.empty:
        raise ValueError(f"Invalid High values found at {len(invalid_high)} timestamps")
    
    # Low should be <= min(Open, Close)
    invalid_low = ha_df[ha_df['Low'] > ha_df[['Open', 'Close']].min(axis=1)]
    if not invalid_low.empty:
        raise ValueError(f"Invalid Low values found at {len(invalid_low)} timestamps")
    
    # Check for NaN values
    if ha_df[required_cols].isnull().any().any():
        raise ValueError("NaN values found in Heikin-Ashi data")
    
    return True


class HeikinAshiConverter:
    """
    Heikin-Ashi Converter Class
    
    Handles conversion of regular OHLC data to Heikin-Ashi format
    with proper validation and error handling.
    """
    
    def __init__(self):
        self.last_conversion_time = None
        self.conversion_count = 0
    
    def convert(self, ohlc_data, validate=True):
        """
        Convert OHLC data to Heikin-Ashi format
        
        Args:
            ohlc_data: DataFrame with OHLC data
            validate: bool, whether to validate the result
            
        Returns:
            DataFrame: Heikin-Ashi converted data
        """
        
        try:
            # Perform conversion
            ha_data = heikin_ashi(ohlc_data)
            
            # Validate if requested
            if validate:
                validate_heikin_ashi(ha_data)
            
            # Update statistics
            self.conversion_count += 1
            self.last_conversion_time = pd.Timestamp.now()
            
            return ha_data
            
        except Exception as e:
            print(f"Heikin-Ashi conversion error: {str(e)}")
            raise
    
    def get_stats(self):
        """Get conversion statistics"""
        return {
            'total_conversions': self.conversion_count,
            'last_conversion': self.last_conversion_time
        }


# Utility functions for Heikin-Ashi analysis
def is_bullish_ha(ha_candle):
    """Check if Heikin-Ashi candle is bullish (green)"""
    return ha_candle['Close'] > ha_candle['Open']


def is_bearish_ha(ha_candle):
    """Check if Heikin-Ashi candle is bearish (red)"""  
    return ha_candle['Close'] < ha_candle['Open']


def ha_trend_strength(ha_df, periods=5):
    """
    Calculate Heikin-Ashi trend strength over specified periods
    
    Returns:
        Series: Trend strength (-1 to 1, where 1 is strong bullish)
    """
    
    bullish = (ha_df['Close'] > ha_df['Open']).astype(int)
    bearish = (ha_df['Close'] < ha_df['Open']).astype(int) * -1
    
    trend_signal = bullish + bearish
    trend_strength = trend_signal.rolling(window=periods).mean()
    
    return trend_strength
