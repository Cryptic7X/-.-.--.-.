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
import asyncio
from datetime import datetime
import yaml
from telegram import Bot
from telegram.constants import ParseMode
from telegram.error import TelegramError
import time


class TelegramAlert:
    """
    Enhanced Telegram Alert System
    
    Handles sending rich, formatted alerts to multiple Telegram channels
    with automatic retry and rate limiting.
    """
    
    def __init__(self, config_path='config/config.yaml'):
        """
        Initialize Telegram alert handler
        
        Args:
            config_path: Path to configuration file
        """
        
        self.config = self._load_config(config_path)
        
        # Bot configuration
        self.bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
        self.standard_chat_id = os.getenv('TELEGRAM_STANDARD_CHAT_ID')
        self.highrisk_chat_id = os.getenv('TELEGRAM_HIGHRISK_CHAT_ID')
        
        if not all([self.bot_token, self.standard_chat_id, self.highrisk_chat_id]):
            print("⚠️  Warning: Telegram credentials not fully configured")
        
        # Initialize bot
        self.bot = Bot(token=self.bot_token) if self.bot_token else None
        
        # Rate limiting
        self.last_message_time = 0
        self.message_delay = 1  # 1 second between messages
        self.max_alerts_per_hour = self.config.get('alerts', {}).get('max_alerts_per_hour', 20)
        
        # Statistics
        self.stats = {
            'messages_sent': 0,
            'errors': 0,
            'last_error': None
        }
    
    def _load_config(self, config_path):
        """Load configuration from YAML file"""
        try:
            with open(config_path, 'r') as f:
                return yaml.safe_load(f)
        except Exception as e:
            print(f"Config loading error: {e}")
            return {}
    
    def _format_currency(self, amount):
        """Format currency amounts with appropriate units"""
        if amount >= 1_000_000_000:
            return f"${amount/1_000_000_000:.1f}B"
        elif amount >= 1_000_000:
            return f"${amount/1_000_000:.0f}M"
        elif amount >= 1_000:
            return f"${amount/1_000:.1f}K"
        else:
            return f"${amount:.2f}"
    
    def _get_signal_emoji(self, signal_type):
        """Get emoji for signal type"""
        return "🟢" if signal_type == "BUY" else "🔴"
    
    def _get_category_header(self, category):
        """Get header for signal category"""
        return "💎 STANDARD" if category == "standard" else "⚡ HIGH-RISK"
    
    def _format_change_24h(self, change_pct):
        """Format 24h price change with color indication"""
        if change_pct > 0:
            return f"+{change_pct:.2f}% 📈"
        elif change_pct < 0:
            return f"{change_pct:.2f}% 📉"
        else:
            return f"{change_pct:.2f}% ➡️"
    
    def _get_stoch_rsi_status(self, stoch_rsi_value, signal_type):
        """Get Stochastic RSI status description"""
        if signal_type == "BUY" and stoch_rsi_value <= 20:
            return f"{stoch_rsi_value:.0f} (Oversold ✅)"
        elif signal_type == "SELL" and stoch_rsi_value >= 80:
            return f"{stoch_rsi_value:.0f} (Overbought ✅)"
        else:
            return f"{stoch_rsi_value:.0f} (Neutral ⚠️)"
    
    def create_alert_message(self, alert_data):
        """
        Create formatted alert message
        
        Args:
            alert_data: Dictionary with alert information
            
        Returns:
            str: Formatted message text
        """
        
        symbol = alert_data['symbol']
        signal_type = alert_data['signal_type'] 
        category = alert_data['category']
        price = alert_data['price']
        change_24h = alert_data['change_24h']
        market_cap = alert_data['market_cap']
        volume = alert_data['volume']
        wt1 = alert_data['wt1']
        wt2 = alert_data['wt2']
        stoch_rsi = alert_data['stoch_rsi']
        tv_link = alert_data.get('tv_link', '')
        
        # Message components
        signal_emoji = self._get_signal_emoji(signal_type)
        category_header = self._get_category_header(category)
        change_text = self._format_change_24h(change_24h)
        stoch_status = self._get_stoch_rsi_status(stoch_rsi, signal_type)
        
        # Current time in IST
        current_time = datetime.now().strftime('%H:%M:%S IST')
        
        # Build message
        message = f"""{signal_emoji} **CipherB {signal_type} SIGNAL** {signal_emoji}

{category_header} | **{symbol}/USDT**
💰 Price: {self._format_currency(price)}
📊 24h Change: {change_text}
🏦 Market Cap: {self._format_currency(market_cap)}
📈 Volume: {self._format_currency(volume)}

**📊 Indicator Values:**
🌊 WaveTrend: wt1={wt1:.1f}, wt2={wt2:.1f}
⚡ Stoch RSI: {stoch_status}

📈 **[Open Chart on TradingView]({tv_link})**

⏰ {current_time}
"""
        
        return message
    
    def send_signal_alert(self, alert_data):
        """
        Send signal alert to appropriate Telegram channel
        
        Args:
            alert_data: Alert data dictionary
            
        Returns:
            bool: True if sent successfully
        """
        
        if not self.bot:
            print("❌ Telegram bot not configured")
            return False
        
        try:
            # Rate limiting
            self._enforce_rate_limit()
            
            # Create message
            message = self.create_alert_message(alert_data)
            
            # Determine target chat
            category = alert_data['category']
            chat_id = self.standard_chat_id if category == 'standard' else self.highrisk_chat_id
            
            # Send message
            asyncio.run(self._send_message_async(chat_id, message))
            
            # Update statistics
            self.stats['messages_sent'] += 1
            
            return True
            
        except Exception as e:
            error_msg = f"Telegram send error: {str(e)}"
            print(f"❌ {error_msg}")
            
            self.stats['errors'] += 1
            self.stats['last_error'] = error_msg
            
            return False
    
    async def _send_message_async(self, chat_id, message):
        """Send message asynchronously"""
        try:
            await self.bot.send_message(
                chat_id=chat_id,
                text=message,
                parse_mode=ParseMode.MARKDOWN_V2,
                disable_web_page_preview=False
            )
        except TelegramError as e:
            # Try without markdown if parsing fails
            if "can't parse" in str(e).lower():
                await self.bot.send_message(
                    chat_id=chat_id,
                    text=message.replace('*', '').replace('`', ''),
                    disable_web_page_preview=False
                )
            else:
                raise
    
    def _enforce_rate_limit(self):
        """Enforce rate limiting between messages"""
        now = time.time()
        elapsed = now - self.last_message_time
        
        if elapsed < self.message_delay:
            time.sleep(self.message_delay - elapsed)
        
        self.last_message_time = time.time()
    
    def send_system_status(self, status_data):
        """
        Send system status message
        
        Args:
            status_data: System status dictionary
            
        Returns:
            bool: Success status
        """
        
        if not self.bot:
            return False
        
        try:
            message = f"""🤖 **Crypto Alert System Status**

📊 **Statistics:**
• Uptime: {status_data.get('uptime', 'Unknown')}
• Coins Processed: {status_data.get('statistics', {}).get('coins_processed', 0):,}
• Signals Detected: {status_data.get('statistics', {}).get('signals_detected', 0)}
• Alerts Sent: {status_data.get('statistics', {}).get('alerts_sent', 0)}

💾 **Cache Status:**
• Age: {status_data.get('cache_stats', {}).get('cache_age_hours', 0):.1f} hours
• Next Refresh: {status_data.get('cache_stats', {}).get('next_refresh_hours', 0):.1f} hours

⏰ {datetime.now().strftime('%H:%M:%S IST')}
"""
            
            # Send to standard channel
            asyncio.run(self._send_message_async(self.standard_chat_id, message))
            
            return True
            
        except Exception as e:
            print(f"Status message error: {e}")
            return False
    
    def test_connection(self):
        """
        Test Telegram bot connection
        
        Returns:
            dict: Test results
        """
        
        if not self.bot:
            return {'success': False, 'error': 'Bot not configured'}
        
        try:
            # Test bot info
            bot_info = asyncio.run(self.bot.get_me())
            
            # Test message sending
            test_message = f"🧪 **Test Message**\n\nBot connection test successful!\n⏰ {datetime.now().strftime('%H:%M:%S IST')}"
            
            asyncio.run(self._send_message_async(self.standard_chat_id, test_message))
            
            return {
                'success': True,
                'bot_username': bot_info.username,
                'bot_name': bot_info.first_name,
                'standard_chat_id': self.standard_chat_id,
                'highrisk_chat_id': self.highrisk_chat_id
            }
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def get_stats(self):
        """Get alert statistics"""
        return self.stats.copy()


# Test function for standalone testing
async def test_telegram_alert():
    """Test the Telegram alert system"""
    
    alert = TelegramAlert()
    
    # Test connection
    connection_test = alert.test_connection()
    print("Connection test:", connection_test)
    
    # Test alert message
    if connection_test['success']:
        test_alert_data = {
            'symbol': 'BTC',
            'signal_type': 'BUY',
            'category': 'standard',
            'price': 43250.75,
            'change_24h': 3.42,
            'market_cap': 850_000_000_000,
            'volume': 25_000_000_000,
            'wt1': -78.2,
            'wt2': -79.1,
            'stoch_rsi': 18,
            'tv_link': 'https://tradingview.com/chart/?symbol=BINANCE:BTCUSDT&interval=1h'
        }
        
        success = alert.send_signal_alert(test_alert_data)
        print(f"Test alert sent: {success}")


if __name__ == "__main__":
    asyncio.run(test_telegram_alert())
