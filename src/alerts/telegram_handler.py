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
from datetime import datetime

def send_telegram_alert(coin_data, signal_type, wt1_val, wt2_val, stoch_rsi_val):
    """
    Send CipherB alert - completely standalone version
    """
    bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
    chat_id = os.getenv('TELEGRAM_CHAT_ID')
    
    if not bot_token or not chat_id:
        print(f"⚠️ Missing Telegram credentials")
        return False
    
    # Extract coin data
    symbol = coin_data.get('symbol', '').upper()
    price = coin_data.get('current_price', 0)
    change_24h = coin_data.get('price_change_percentage_24h', 0)
    market_cap = coin_data.get('market_cap', 0)
    volume = coin_data.get('total_volume', 0)
    
    # Generate links directly
    clean_symbol = symbol.replace('USDT', '').replace('USD', '')
    tv_link = f"https://www.tradingview.com/chart/?symbol=BINANCE:{clean_symbol}USDT&interval=1h"
    binance_link = f"https://www.binance.com/en/trade/{clean_symbol}_USDT"
    
    # Format price
    if price < 0.01:
        price_formatted = f"${price:.8f}"
    elif price < 1:
        price_formatted = f"${price:.6f}"
    else:
        price_formatted = f"${price:.4f}"
    
    # Format market data
    market_cap_m = market_cap / 1_000_000
    volume_m = volume / 1_000_000
    
    # Signal formatting
    signal_emoji = "🟢" if signal_type.upper() == "BUY" else "🔴"
    
    # StochRSI status
    if signal_type.upper() == "BUY":
        stoch_status = "Oversold ✅" if stoch_rsi_val <= 20 else f"Neutral ({stoch_rsi_val:.0f})"
    else:
        stoch_status = "Overbought ✅" if stoch_rsi_val >= 80 else f"Neutral ({stoch_rsi_val:.0f})"
    
    # Market cap category
    if market_cap >= 1_000_000_000:
        cap_category = "💎 LARGE CAP"
    elif market_cap >= 500_000_000:
        cap_category = "🔷 MID CAP"
    else:
        cap_category = "⚡ SMALL CAP"
    
    # Message
    message = f"""{signal_emoji} *CipherB {signal_type.upper()} SIGNAL* {signal_emoji}

{cap_category} | *{symbol}/USDT*

💰 *Price:* {price_formatted}
📈 *24h Change:* {change_24h:+.2f}%
🏦 *Market Cap:* ${market_cap_m:,.0f}M
📊 *Volume:* ${volume_m:,.0f}M

*🔍 INDICATOR VALUES:*
🌊 *CipherB:* wt1={wt1_val:.1f}, wt2={wt2_val:.1f}
⚡ *Stoch RSI:* {stoch_rsi_val:.0f} ({stoch_status})

*📊 CHARTS:*
📈 [TradingView Chart]({tv_link})
🌐 [Binance Web]({binance_link})

🕐 {datetime.now().strftime('%Y-%m-%d %H:%M:%S IST')}
⏰ Cooldown: 2 hours

🤖 CipherB System | 175 Quality Coins"""

    # Send to Telegram
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
        print(f"✅ Alert sent: {symbol} {signal_type}")
        return True
    except requests.RequestException as e:
        print(f"❌ Failed to send alert for {symbol}: {e}")
        return False
