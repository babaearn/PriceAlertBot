"""
Control Command Handlers
/start - Welcome message
/help - Help information
/pause - Pause price scanner
/resume - Resume price scanner
/status - Check scanner status
"""

import logging
from telegram import Update
from telegram.ext import ContextTypes
from bot.utils.validators import is_admin
from bot.services.database import set_config_value, get_config_value

logger = logging.getLogger(__name__)

# Global reference to price monitor (set by main.py)
price_monitor = None


def set_price_monitor(monitor):
    """Set global price monitor reference"""
    global price_monitor
    price_monitor = monitor


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Welcome message"""
    await update.message.reply_text(
        "🤖 <b>Telegram Price Alert Bot</b>\n\n"
        "Automated cryptocurrency price monitoring with real-time alerts.\n\n"
        "Use /help to see available commands.",
        parse_mode='HTML'
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Help information"""
    user_id = update.effective_user.id
    is_user_admin = is_admin(user_id)

    help_text = """
🤖 <b>Available Commands</b>

<b>General:</b>
/start - Welcome message
/help - Show this help
/status - Check scanner status
/stats - View statistics
/listpairs - Show all monitored pairs
"""

    if is_user_admin:
        help_text += """
<b>Admin Commands:</b>
/addnew - Add new pair(s)
  • Single: /addnew BTC https://link.com/btc
  • Bulk: /addnew BTC link1 ETH link2

/removepair - Remove pair
  • /removepair BTC

/cooldown - Set alert cooldown
  • /cooldown 30m
  • /cooldown 1h
  • /cooldown off

/pause - Pause scanner
/resume - Resume scanner
"""

    help_text += """
<b>Features:</b>
• 30-second price monitoring
• Session-based alerts (resets daily at 00:00 UTC)
• Volume filtering ($5M minimum)
• Bybit + Binance fallback APIs
"""

    await update.message.reply_text(help_text.strip(), parse_mode='HTML')


async def pause_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Pause price scanner"""
    user_id = update.effective_user.id

    # Check admin permission
    if not is_admin(user_id):
        await update.message.reply_text("❌ Access denied. Admin only.")
        return

    if price_monitor:
        price_monitor.pause()
        set_config_value('scanner_status', 'paused', str(user_id))
        await update.message.reply_text("⏸️ Scanner paused")
    else:
        await update.message.reply_text("❌ Scanner not initialized")


async def resume_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Resume price scanner"""
    user_id = update.effective_user.id

    # Check admin permission
    if not is_admin(user_id):
        await update.message.reply_text("❌ Access denied. Admin only.")
        return

    if price_monitor:
        price_monitor.resume()
        set_config_value('scanner_status', 'running', str(user_id))
        await update.message.reply_text("▶️ Scanner resumed")
    else:
        await update.message.reply_text("❌ Scanner not initialized")


async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Check scanner status"""
    if not price_monitor:
        await update.message.reply_text("❌ Scanner not initialized")
        return

    status = price_monitor.get_status()

    status_icon = "▶️" if status['running'] else "⏸️"
    status_text = "Running" if status['running'] else "Paused"

    message = f"""
📊 <b>Scanner Status</b>

Status: {status_icon} {status_text}
Scan Count: #{status['scan_count']}
Interval: {status['scan_interval']}s

Last Updated: {get_config_value('updated_at', 'N/A')}
"""

    await update.message.reply_text(message.strip(), parse_mode='HTML')
