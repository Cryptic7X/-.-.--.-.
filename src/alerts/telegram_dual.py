"""
Dual Confirmation Telegram Alert System
Enhanced alerts showing both CipherB and StochRSI confirmation details
"""

import os
import requests
from datetime import datetime, timedelta

def get_ist_time():
    """Convert UTC to IST"""
    return datetime.utcnow() + timedelta(hours=5, minutes=30)

def send_dual_confirmation_alert(all_signals):
    """
    Send consolidated dual confirmation alert with StochRSI details
    """
    bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
    chat_id = os.getenv('TELEGRAM_CHAT_ID')  # Updated env var
    
    if not bot_token or not chat_id or not all_signals:
        print("❌ Missing Telegram credentials or no signals")
        return False

    # Current time
    ist_time = get_ist_time()
    current_time_str = ist_time.strftime('%H:%M:%S IST')

    # Group signals
    buy_signals = [s for s in all_signals if s['signal_type'] == 'BUY']
    sell_signals = [s for s in all_signals if s['signal_type'] == 'SELL']
    
    # Count confirmation types
    stochrsi_confirmed = len([s for s in all_signals if s['stochrsi_status'] == 'confirmed'])
    cipherb_fallback = len([s for s in all_signals if s['stochrsi_status'] in ['unavailable', 'calc_error']])

    # Build message
    message = f"""🎯 *DUAL CONFIRMATION ALERT*
🚨 *{len(all_signals)} PRECISE SIGNALS*
🕐 *{current_time_str}*

"""

    # BUY signals
    if buy_signals:
        message += "🟢 *BUY SIGNALS:*\n"
        for i, signal in enumerate(buy_signals, 1):
            symbol = signal['symbol']
            price = signal['price']
            change_24h = signal['change_24h']
            market_cap_m = signal['market_cap'] / 1_000_000 if signal['market_cap'] else 0
            wt1 = signal['wt1']
            wt2 = signal['wt2']
            exchange = signal['exchange']
            stochrsi_status = signal['stochrsi_status']
            stochrsi_d = signal['stochrsi_d_value']
            age_s = signal['signal_age_seconds']

            # Price formatting
            if price < 0.001:
                price_fmt = f"${price:.8f}"
            elif price < 1:
                price_fmt = f"${price:.4f}"
            else:
                price_fmt = f"${price:.3f}"

            # StochRSI status formatting
            if stochrsi_status == "confirmed":
                stochrsi_text = f"StochRSI: D={stochrsi_d:.1f} ✅"
            elif stochrsi_status == "unavailable":
                stochrsi_text = "StochRSI: No 3h data ⚠️"
            elif stochrsi_status == "calc_error":
                stochrsi_text = "StochRSI: Calc error ⚠️"
            else:
                stochrsi_text = f"StochRSI: D={stochrsi_d:.1f} ❌"

            # TradingView link
            clean_symbol = symbol.replace('USDT', '').replace('USD', '')
            tv_link = f"https://www.tradingview.com/chart/?symbol={clean_symbol}USDT&interval=15"

            message += f"""
{i}. *{symbol}* | {price_fmt} | {change_24h:+.1f}%
   Cap: ${market_cap_m:.0f}M | WT: {wt1:.1f}/{wt2:.1f}
   {stochrsi_text} | ⚡{age_s:.0f}s ago
   {exchange} | [Chart →]({tv_link})"""

    # SELL signals
    if sell_signals:
        message += f"\n\n🔴 *SELL SIGNALS:*\n"
        for i, signal in enumerate(sell_signals, 1):
            symbol = signal['symbol']
            price = signal['price']
            change_24h = signal['change_24h']
            market_cap_m = signal['market_cap'] / 1_000_000 if signal['market_cap'] else 0
            wt1 = signal['wt1']
            wt2 = signal['wt2']
            exchange = signal['exchange']
            stochrsi_status = signal['stochrsi_status']
            stochrsi_d = signal['stochrsi_d_value']
            age_s = signal['signal_age_seconds']

            # Price formatting
            if price < 0.001:
                price_fmt = f"${price:.8f}"
            elif price < 1:
                price_fmt = f"${price:.4f}"
            else:
                price_fmt = f"${price:.3f}"

            # StochRSI status formatting
            if stochrsi_status == "confirmed":
                stochrsi_text = f"StochRSI: D={stochrsi_d:.1f} ✅"
            elif stochrsi_status == "unavailable":
                stochrsi_text = "StochRSI: No 3h data ⚠️"
            elif stochrsi_status == "calc_error":
                stochrsi_text = "StochRSI: Calc error ⚠️"
            else:
                stochrsi_text = f"StochRSI: D={stochrsi_d:.1f} ❌"

            # TradingView link
            clean_symbol = symbol.replace('USDT', '').replace('USD', '')
            tv_link = f"https://www.tradingview.com/chart/?symbol={clean_symbol}USDT&interval=15"

            message += f"""
{i}. *{symbol}* | {price_fmt} | {change_24h:+.1f}%
   Cap: ${market_cap_m:.0f}M | WT: {wt1:.1f}/{wt2:.1f}
   {stochrsi_text} | ⚡{age_s:.0f}s ago
   {exchange} | [Chart →]({tv_link})"""

    # Footer
    message += f"""

📊 *CONFIRMATION SUMMARY:*
• Total Signals: {len(all_signals)} | Buy: {len(buy_signals)} | Sell: {len(sell_signals)}
• StochRSI Confirmed: {stochrsi_confirmed} ✅
• CipherB Fallback: {cipherb_fallback} ⚠️

🎯 *DUAL SYSTEM STATUS:*
• CipherB 15m: Exact Pine Script logic ✅
• StochRSI 3h: %D confirmation (≤30 buy, ≥70 sell) ✅
• Timing: Fresh signals within 2 minutes ✅

🔧 *Dual Confirmation System v1.0*"""

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
        print(f"📱 Dual confirmation alert sent: {len(all_signals)} signals")
        return True
    except Exception as e:
        print(f"❌ Telegram alert failed: {e}")
        return False
