"""
Professional Telegram Alert System for 2H CipherB Analysis
Pure CipherB signals - no confirmation needed
"""

import os
import requests
from datetime import datetime

def send_professional_alert(coin_data, signal_type, wt1_val, wt2_val, exchange_used, signal_timestamp):
    """
    Send professional-grade 2H CipherB alert (Pure signals)
    """
    bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
    chat_id = os.getenv('TELEGRAM_CHAT_ID')
    
    if not bot_token or not chat_id:
        print("⚠️ Professional alert system: Missing Telegram credentials")
        return False
    
    # Extract professional coin data
    symbol = coin_data.get('symbol', '').upper()
    price = coin_data.get('current_price', 0)
    change_24h = coin_data.get('price_change_percentage_24h', 0)
    market_cap = coin_data.get('market_cap', 0)
    volume = coin_data.get('total_volume', 0)
    
    # Professional price formatting
    if price < 0.01:
        price_formatted = f"${price:.8f}"
    elif price < 1:
        price_formatted = f"${price:.6f}"
    else:
        price_formatted = f"${price:.4f}"
    
    # Professional market data formatting
    market_cap_m = market_cap / 1_000_000
    volume_m = volume / 1_000_000
    
    # Professional signal formatting
    signal_emoji = "🟢 📈" if signal_type.upper() == "BUY" else "🔴 📉"
    
    # Professional market cap classification
    if market_cap >= 5_000_000_000:
        cap_class = "🏆 MEGA CAP"
    elif market_cap >= 1_000_000_000:
        cap_class = "💎 LARGE CAP"
    elif market_cap >= 500_000_000:
        cap_class = "🔷 MID CAP"
    else:
        cap_class = "⚡ GROWTH CAP"
    
    # Professional 2H chart links (interval=120 for 2H)
    clean_symbol = symbol.replace('USDT', '').replace('USD', '')
    tv_2h_link = f"https://www.tradingview.com/chart/?symbol={clean_symbol}USDT&interval=120"
    
    # Professional alert message for 2H pure CipherB
    message = f"""{signal_emoji} *PURE CIPHERB {signal_type.upper()}*

🎯 *{symbol}/USDT* | {cap_class}
📊 *2-HOUR TIMEFRAME ANALYSIS*

💰 *Market Data:*
   • Price: {price_formatted}
   • 24h Change: {change_24h:+.2f}%
   • Market Cap: ${market_cap_m:,.0f}M
   • Volume: ${volume_m:,.0f}M

🔍 *PURE CIPHERB SIGNAL:*
   🌊 *WaveTrend Values:*
      • wt1: {wt1_val:.1f}
      • wt2: {wt2_val:.1f}
   ✅ *Back-Tested & Validated*

📊 *ANALYSIS DETAILS:*
   • Data Source: {exchange_used}
   • Signal Time: {signal_timestamp.strftime('%H:%M IST')}
   • Timeframe: 2H Professional
   • Method: Pure CipherB (No Confirmation)

📈 *PROFESSIONAL CHART:*
   • [TradingView 2H Chart]({tv_2h_link})

🕐 {datetime.now().strftime('%Y-%m-%d %H:%M:%S IST')}
⏰ Cooldown: 3 hours

─────────────────────────────
🤖 *CipherB Professional System v2.1*
📊 2H Analysis | 175 Quality Coins | Pure Signals
🎯 Back-Tested Private Indicator"""

    # Professional alert dispatch
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
        print(f"✅ Professional alert dispatched: {symbol} {signal_type}")
        return True
    except requests.RequestException as e:
        print(f"❌ Professional alert failed for {symbol}: {e}")
        return False
