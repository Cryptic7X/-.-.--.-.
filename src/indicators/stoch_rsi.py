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
    Calculate Relative Strength Index (RSI)
    
    Args:
        series: Price series (typically Close prices)
        period: RSI calculation period (default 14)
        
    Returns:
        pandas.Series: RSI values (0-100)
    """
    
    delta = series.diff()
    gain = delta.where(delta > 0, 0)
    loss = -delta.where(delta < 0, 0)
    
    avg_gain = gain.rolling(window=period).mean()
    avg_loss = loss.rolling(window=period).mean()
    
    # Handle division by zero
    rs = avg_gain / avg_loss.replace(0, np.inf)
    rsi_values = 100 - (100 / (1 + rs))
    
    return rsi_values


def stochastic(high_series, low_series, close_series, period=14):
    """
    Calculate Stochastic oscillator %K
    
    Args:
        high_series: High price series
        low_series: Low price series  
        close_series: Close price series
        period: Stochastic period
        
    Returns:
        pandas.Series: Stochastic %K values (0-100)
    """
    
    lowest_low = low_series.rolling(window=period).min()
    highest_high = high_series.rolling(window=period).max()
    
    # Avoid division by zero
    denominator = highest_high - lowest_low
    denominator = denominator.replace(0, np.inf)
    
    stoch_k = ((close_series - lowest_low) / denominator) * 100
    
    return stoch_k


def stochastic_rsi(price_series, 
                  rsi_period=14, 
                  stoch_period=14, 
                  k_period=3, 
                  d_period=3):
    """
    Calculate Stochastic RSI indicator
    
    This combines RSI and Stochastic oscillator to create a more sensitive
    momentum indicator for overbought/oversold conditions.
    
    Args:
        price_series: Price data (typically Close prices)
        rsi_period: RSI calculation period (default 14)
        stoch_period: Stochastic period for RSI values (default 14)  
        k_period: %K smoothing period (default 3)
        d_period: %D smoothing period (default 3)
        
    Returns:
        dict: Contains 'stoch_rsi_k' and 'stoch_rsi_d' Series
    """
    
    # Step 1: Calculate RSI
    rsi_values = rsi(price_series, rsi_period)
    
    # Step 2: Apply Stochastic to RSI values
    # For Stochastic RSI, we use RSI as high, low, and close
    stoch_k_raw = stochastic(rsi_values, rsi_values, rsi_values, stoch_period)
    
    # Step 3: Smooth %K with SMA
    stoch_rsi_k = stoch_k_raw.rolling(window=k_period).mean()
    
    # Step 4: Calculate %D as SMA of %K
    stoch_rsi_d = stoch_rsi_k.rolling(window=d_period).mean()
    
    return {
        'stoch_rsi_k': stoch_rsi_k,
        'stoch_rsi_d': stoch_rsi_d,
        'rsi': rsi_values
    }


def detect_stoch_rsi_signals(price_data, 
                            oversold_level=20, 
                            overbought_level=80,
                            **kwargs):
    """
    Detect Stochastic RSI overbought/oversold signals
    
    Args:
        price_data: DataFrame or Series with price data
        oversold_level: Oversold threshold (default 20)
        overbought_level: Overbought threshold (default 80)
        **kwargs: Additional parameters for stochastic_rsi()
        
    Returns:
        pandas.DataFrame: Signals and indicator values
    """
    
    # Handle DataFrame input (use Close column)
    if isinstance(price_data, pd.DataFrame):
        if 'Close' in price_data.columns:
            price_series = price_data['Close']
        else:
            raise ValueError("DataFrame must contain 'Close' column")
    else:
        price_series = price_data
    
    # Calculate Stochastic RSI
    stoch_rsi_data = stochastic_rsi(price_series, **kwargs)
    
    # Create signals DataFrame
    signals_df = pd.DataFrame(index=price_series.index)
    signals_df['stoch_rsi_k'] = stoch_rsi_data['stoch_rsi_k']
    signals_df['stoch_rsi_d'] = stoch_rsi_data['stoch_rsi_d'] 
    signals_df['rsi'] = stoch_rsi_data['rsi']
    
    # Generate signals based on %K line
    signals_df['oversold'] = signals_df['stoch_rsi_k'] <= oversold_level
    signals_df['overbought'] = signals_df['stoch_rsi_k'] >= overbought_level
    
    # Signal confirmation (both %K and %D in extreme zones)
    signals_df['oversold_confirmed'] = (
        (signals_df['stoch_rsi_k'] <= oversold_level) & 
        (signals_df['stoch_rsi_d'] <= oversold_level)
    )
    
    signals_df['overbought_confirmed'] = (
        (signals_df['stoch_rsi_k'] >= overbought_level) &
        (signals_df['stoch_rsi_d'] >= overbought_level) 
    )
    
    return signals_df


class StochRSIIndicator:
    """
    Stochastic RSI Indicator Class
    
    Provides Stochastic RSI calculations and signal generation
    for use as confirmation with CipherB signals.
    """
    
    def __init__(self,
                 rsi_period=14,
                 stoch_period=14,
                 k_period=3,
                 d_period=3,
                 oversold_level=20,
                 overbought_level=80):
        """
        Initialize Stochastic RSI indicator
        
        Args:
            rsi_period: RSI calculation period
            stoch_period: Stochastic period for RSI values
            k_period: %K smoothing period  
            d_period: %D smoothing period
            oversold_level: Oversold threshold
            overbought_level: Overbought threshold
        """
        
        self.rsi_period = rsi_period
        self.stoch_period = stoch_period
        self.k_period = k_period
        self.d_period = d_period
        self.oversold_level = oversold_level
        self.overbought_level = overbought_level
    
    def calculate(self, price_data):
        """
        Calculate Stochastic RSI values
        
        Args:
            price_data: Price data (DataFrame or Series)
            
        Returns:
            DataFrame: Stochastic RSI signals and values
        """
        
        try:
            signals = detect_stoch_rsi_signals(
                price_data,
                oversold_level=self.oversold_level,
                overbought_level=self.overbought_level,
                rsi_period=self.rsi_period,
                stoch_period=self.stoch_period,
                k_period=self.k_period,
                d_period=self.d_period
            )
            
            return signals
            
        except Exception as e:
            print(f"Stochastic RSI calculation error: {str(e)}")
            return None
    
    def get_latest_signal(self, price_data):
        """
        Get the most recent Stochastic RSI signal
        
        Returns:
            dict: Latest signal information or None
        """
        
        signals = self.calculate(price_data)
        if signals is None:
            return None
        
        latest = signals.iloc[-1]
        
        signal_info = {
            'stoch_rsi_k': latest['stoch_rsi_k'],
            'stoch_rsi_d': latest['stoch_rsi_d'],
            'rsi': latest['rsi'],
            'timestamp': latest.name
        }
        
        if latest['oversold_confirmed']:
            signal_info['confirmation'] = 'OVERSOLD'
            signal_info['buy_confirmation'] = True
        elif latest['overbought_confirmed']:
            signal_info['confirmation'] = 'OVERBOUGHT'
            signal_info['sell_confirmation'] = True
        else:
            signal_info['confirmation'] = 'NEUTRAL'
            signal_info['buy_confirmation'] = False
            signal_info['sell_confirmation'] = False
        
        return signal_info
    
    def is_oversold(self, price_data):
        """Check if current Stochastic RSI is oversold"""
        latest = self.get_latest_signal(price_data)
        return latest and latest.get('buy_confirmation', False)
    
    def is_overbought(self, price_data):
        """Check if current Stochastic RSI is overbought"""
        latest = self.get_latest_signal(price_data)
        return latest and latest.get('sell_confirmation', False)
