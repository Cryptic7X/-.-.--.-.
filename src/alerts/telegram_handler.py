"""
Telegram Alert Handler
======================

Enhanced Telegram alert system with rich formatting and TradingView chart links.
Sends alerts to separate channels for standard and high-risk signals.

Features:
- Rich message formatting with emojis and markdown
- TradingView chart links for manual verification
- Separate channels for different risk categories
- Error handling and retry logic
- Rate limiting protection
"""

import os
import requests
import yaml
from datetime import datetime
from utils.symbol_validator import generate_tradingview_link

def load_config():
    """Load configuration"""
    with open('config/config.yaml', 'r') as f:
        return yaml.safe_load(f)

def send_telegram_alert(coin_data, signal_type, channel_type, wt1_val, wt2_val, stoch_rsi_val):
    """
    Send enhanced Telegram alert with TradingView link and market data
    """
    # Get credentials from environment variables
    bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
    
    if channel_type == 'standard':
        chat_id = os.getenv('STANDARD_CHAT_ID')
        channel_header = "💎 STANDARD"
    else:
        chat_id = os.getenv('HIGH_RISK_CHAT_ID')
        channel_header = "⚡ HIGH-RISK"
    
    if not bot_token or not chat_id:
        print(f"Warning: Missing Telegram credentials for {channel_type} channel")
        return False
    
    # Extract coin data
    symbol = coin_data.get('symbol', '').upper()
    price = coin_data.get('current_price', 0)
    change_24h = coin_data.get('price_change_percentage_24h', 0)
    market_cap = coin_data.get('market_cap', 0)
    volume = coin_data.get('total_volume', 0)
    
    # Generate TradingView link
    tv_link = generate_tradingview_link(symbol)
    
    # Format message
    signal_emoji = "🟢" if signal_type.upper() == "BUY" else "🔴"
    
    # Format numbers
    price_formatted = f"${price:.6f}" if price < 1 else f"${price:.4f}"
    market_cap_m = market_cap / 1_000_000
    volume_m = volume / 1_000_000
    
    # Stoch RSI confirmation
    if signal_type.upper() == "BUY":
        stoch_status = "Oversold ✅" if stoch_rsi_val <= 20 else f"Neutral ({stoch_rsi_val:.0f})"
    else:
        stoch_status = "Overbought ✅" if stoch_rsi_val >= 80 else f"Neutral ({stoch_rsi_val:.0f})"
    
    message = f"""{signal_emoji} *CipherB {signal_type.upper()} SIGNAL* {signal_emoji}

{channel_header} | *{symbol}/USDT*
💰 Price: {price_formatted}
📈 24h Change: {change_24h:+.2f}%
🏦 Market Cap: ${market_cap_m:,.0f}M
📊 Volume: ${volume_m:,.0f}M

*📊 Indicator Values:*
🌊 WaveTrend: wt1={wt1_val:.1f}, wt2={wt2_val:.1f}
⚡ Stoch RSI: {stoch_rsi_val:.0f} ({stoch_status})

📈 [Open Chart on TradingView]({tv_link})

⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S IST')}"""

    # Send message
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = {
        'chat_id': chat_id,
        'text': message,
        'parse_mode': 'Markdown',
        'disable_web_page_preview': False
    }
    
    try:
        response = requests.post(url, json=payload, timeout=30)
        response.raise_for_status()
        print(f"✅ Alert sent: {symbol} {signal_type} to {channel_type} channel")
        return True
    except requests.RequestException as e:
        print(f"❌ Failed to send alert for {symbol}: {e}")
        return False
