"""
Professional Telegram Alert System for 4H CipherB Analysis
"""

import os
import requests
from datetime import datetime

def send_professional_alert(coin_data, signal_type, wt1_val, wt2_val, stoch_rsi_val, exchange_used, signal_timestamp):
    """
    Send professional-grade 4H CipherB alert
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
    
    # Professional StochRSI status
    if signal_type.upper() == "BUY":
        stoch_status = "Oversold Confirmed ✅" if stoch_rsi_val <= 20 else f"Moderate ({stoch_rsi_val:.0f})"
    else:
        stoch_status = "Overbought Confirmed ✅" if stoch_rsi_val >= 80 else f"Moderate ({stoch_rsi_val:.0f})"
    
    # Professional market cap classification
    if market_cap >= 5_000_000_000:
        cap_class = "🏆 MEGA CAP"
    elif market_cap >= 1_000_000_000:
        cap_class = "💎 LARGE CAP"
    elif market_cap >= 500_000_000:
        cap_class = "🔷 MID CAP"
    else:
        cap_class = "⚡ GROWTH CAP"
    
    # Professional chart links
    clean_symbol = symbol.replace('USDT', '').replace('USD', '')
    tv_4h_link = f"https://www.tradingview.com/chart/?symbol=BINANCE:{clean_symbol}USDT&interval=240"  # 4H = 240 minutes
    binance_link = f"https://www.binance.com/en/trade/{clean_symbol}_USDT"
    
    # Professional alert message
    message = f"""{signal_emoji} *PROFESSIONAL CIPHERB {signal_type.upper()}*

🎯 *{symbol}/USDT* | {cap_class}
📊 *4-HOUR TIMEFRAME ANALYSIS*

💰 *Market Data:*
   • Price: {price_formatted}
   • 24h Change: {change_24h:+.2f}%
   • Market Cap: ${market_cap_m:,.0f}M
   • Volume: ${volume_m:,.0f}M

🔍 *PROFESSIONAL INDICATORS:*
   🌊 *CipherB WaveTrend:*
      • wt1: {wt1_val:.1f}
      • wt2: {wt2_val:.1f}
   ⚡ *Stoch RSI:* {stoch_rsi_val:.0f} ({stoch_status})

📊 *ANALYSIS DETAILS:*
   • Data Source: {exchange_used}
   • Signal Time: {signal_timestamp.strftime('%H:%M IST')}
   • Timeframe: 4H Professional
   • Confirmation: Dual Indicator ✅

📈 *PROFESSIONAL CHARTS:*
   • [TradingView 4H Chart]({tv_4h_link})
   • [Binance Trading]({binance_link})

🕐 {datetime.now().strftime('%Y-%m-%d %H:%M:%S IST')}
⏰ Cooldown: 2 hours

─────────────────────────────
🤖 *CipherB Professional System v2.0*
📊 4H Analysis | 175 Quality Coins | 100M+ Cap
🎯 Professional Grade Trading Signals"""

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
