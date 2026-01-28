"""
Control Command Handlers
/start - Welcome message
/help - Help information
/pause - Pause price scanner
/resume - Resume price scanner
/status - Check scanner status
/test - Health check for all services
"""

import logging
import time
from telegram import Update
from telegram.ext import ContextTypes
from bot.utils.validators import is_admin
from bot.services.database import set_config_value, get_config_value, get_connection, get_active_pairs
from bot.services.price_fetcher import PriceFetcher

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
🤖 <b>Price Alert Bot - Commands</b>

<b>📊 Status Commands:</b>
/start - Welcome message
/help - Show this help
/status - Check scanner status
/stats - View statistics
/logs - View recent deployment logs
/test - Health check all services
"""

    if is_user_admin:
        help_text += """
<b>🔧 Admin Commands:</b>

<b>Scanner Control:</b>
/pause - Pause price scanning
/resume - Resume price scanning
/interval &lt;time&gt; - Set scan interval
  • /interval 30s or /interval 1m

<b>Configuration:</b>
/volume &lt;amount&gt; - Set volume threshold
  • /volume 5M or /volume 10M
/show - Show filtered pairs
/show all - List all 474+ pairs
/show stats - Detailed statistics

<b>Session Management:</b>
/resetsession - Reset to current prices
/syncprices - Info about session sync

<b>Pair Management:</b>
/addnew - Add new pair(s)
/removepair - Remove pair
/cooldown - Set alert cooldown

<b>Testing:</b>
/testalert - Send test alert
"""

    help_text += """
<b>💡 How It Works:</b>
• Scans every 30 seconds (configurable)
• Session resets daily at 00:00 UTC
• Only pairs with $5M+ volume monitored
• Alerts at: ±10%, ±30%, ±60%, ±80%, ±100%
• Then every ±50% beyond 100%
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


async def test_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Health check - Tests all API functions and services
    Shows results for: Database, Bybit API, Binance API, Telegram
    """
    await update.message.reply_text("🔄 <b>Running health checks...</b>", parse_mode='HTML')

    results = []
    total_start = time.time()

    # ========== 1. DATABASE TEST ==========
    db_status = "❌ Failed"
    db_time = 0
    db_details = ""
    try:
        start = time.time()
        conn = get_connection()
        conn.close()
        db_time = (time.time() - start) * 1000  # ms

        # Get active pairs count
        pairs = get_active_pairs()
        db_status = "✅ Connected"
        db_details = f"({len(pairs)} active pairs)"
    except Exception as e:
        db_status = "❌ Failed"
        db_details = f"({str(e)[:50]})"

    results.append(f"<b>1. Database</b>\n   {db_status} {db_details}\n   ⏱ {db_time:.0f}ms")

    # ========== 2. BYBIT API TEST ==========
    bybit_status = "❌ Failed"
    bybit_time = 0
    bybit_details = ""
    try:
        start = time.time()
        fetcher = PriceFetcher()
        ticker = fetcher.bybit.fetch_ticker('BTC/USDT')
        bybit_time = (time.time() - start) * 1000

        if ticker and ticker.get('last'):
            price = ticker['last']
            bybit_status = "✅ Online"
            bybit_details = f"(BTC: ${price:,.2f})"
        else:
            bybit_status = "⚠️ No data"
    except Exception as e:
        bybit_status = "❌ Failed"
        bybit_details = f"({str(e)[:50]})"

    results.append(f"<b>2. Bybit API</b>\n   {bybit_status} {bybit_details}\n   ⏱ {bybit_time:.0f}ms")

    # ========== 3. BINANCE API TEST ==========
    binance_status = "❌ Failed"
    binance_time = 0
    binance_details = ""
    try:
        start = time.time()
        fetcher = PriceFetcher()
        ticker = fetcher.binance.fetch_ticker('BTC/USDT')
        binance_time = (time.time() - start) * 1000

        if ticker and ticker.get('last'):
            price = ticker['last']
            binance_status = "✅ Online"
            binance_details = f"(BTC: ${price:,.2f})"
        else:
            binance_status = "⚠️ No data"
    except Exception as e:
        binance_status = "❌ Failed"
        binance_details = f"({str(e)[:50]})"

    results.append(f"<b>3. Binance API</b>\n   {binance_status} {binance_details}\n   ⏱ {binance_time:.0f}ms")

    # ========== 4. TELEGRAM BOT TEST ==========
    tg_status = "✅ Online"
    tg_details = "(message sent)"
    tg_time = (time.time() - total_start) * 1000  # Approximate

    results.append(f"<b>4. Telegram Bot</b>\n   {tg_status} {tg_details}\n   ⏱ {tg_time:.0f}ms")

    # ========== 5. SCANNER STATUS ==========
    scanner_status = "❌ Not initialized"
    if price_monitor:
        status = price_monitor.get_status()
        if status['running']:
            scanner_status = f"✅ Running (Scan #{status['scan_count']})"
        else:
            scanner_status = "⏸️ Paused"

    results.append(f"<b>5. Price Scanner</b>\n   {scanner_status}")

    # ========== SUMMARY ==========
    total_time = (time.time() - total_start) * 1000

    # Count passed/failed
    passed = sum(1 for r in results if "✅" in r)
    total = len(results)

    summary_emoji = "✅" if passed == total else "⚠️" if passed >= 3 else "❌"

    message = f"""
{summary_emoji} <b>Health Check Results</b>

{chr(10).join(results)}

━━━━━━━━━━━━━━━━━━━━
<b>Summary:</b> {passed}/{total} services healthy
<b>Total time:</b> {total_time:.0f}ms
"""

    await update.message.reply_text(message.strip(), parse_mode='HTML')
