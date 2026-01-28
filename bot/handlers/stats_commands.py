"""
Statistics Command Handlers
/stats - View bot statistics
/listpairs - Show all monitored pairs
/logs - View recent deployment logs (last 50 entries)
"""

import logging
from pathlib import Path
from telegram import Update
from telegram.ext import ContextTypes
from bot.services.database import get_stats, get_active_pairs
from bot.utils.formatters import format_stats, format_pair_list

logger = logging.getLogger(__name__)


async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """View bot statistics"""
    try:
        stats = get_stats()
        message = format_stats(stats)
        await update.message.reply_text(message, parse_mode='HTML')

    except Exception as e:
        logger.error(f"Error in stats command: {e}")
        await update.message.reply_text(f"❌ Error fetching stats: {e}")


async def listpairs_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show all monitored pairs grouped by letter"""
    try:
        pairs = get_active_pairs()
        message = format_pair_list(pairs)

        # Split message if too long (Telegram limit: 4096 chars)
        if len(message) > 4000:
            # Split by groups
            chunks = message.split('\n\n')
            current_chunk = chunks[0] + '\n\n'

            for chunk in chunks[1:]:
                if len(current_chunk) + len(chunk) + 2 < 4000:
                    current_chunk += chunk + '\n\n'
                else:
                    await update.message.reply_text(current_chunk.strip(), parse_mode='HTML')
                    current_chunk = chunk + '\n\n'

            if current_chunk.strip():
                await update.message.reply_text(current_chunk.strip(), parse_mode='HTML')
        else:
            await update.message.reply_text(message, parse_mode='HTML')

    except Exception as e:
        logger.error(f"Error in listpairs command: {e}")
        await update.message.reply_text(f"❌ Error fetching pairs: {e}")


async def logs_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """View recent deployment logs for debugging"""
    try:
        from bot.services.log_writer import get_recent_logs

        # Get recent logs
        recent_logs = get_recent_logs()

        if not recent_logs:
            await update.message.reply_text("📝 No logs captured yet. Logs are captured every scan cycle.")
            return

        # Take last 50 entries
        last_logs = recent_logs[-50:]

        # Format as code block
        message = f"📝 <b>Recent Deployment Logs</b>\n\n<code>"
        for log_entry in last_logs:
            # Truncate very long lines
            if len(log_entry) > 200:
                log_entry = log_entry[:197] + "..."
            message += log_entry + "\n"

        message += "</code>\n\n"
        message += f"<i>Showing last {len(last_logs)} of {len(recent_logs)} total logs</i>"

        # Split if too long
        if len(message) > 4000:
            chunks = []
            current = "📝 <b>Recent Deployment Logs</b>\n\n<code>"

            for log_entry in last_logs:
                if len(log_entry) > 200:
                    log_entry = log_entry[:197] + "..."

                if len(current) + len(log_entry) + 10 < 3900:
                    current += log_entry + "\n"
                else:
                    current += "</code>"
                    chunks.append(current)
                    current = "<code>" + log_entry + "\n"

            if current != "<code>":
                current += "</code>"
                chunks.append(current)

            for i, chunk in enumerate(chunks):
                await update.message.reply_text(
                    chunk + f"\n\n<i>Part {i+1}/{len(chunks)}</i>",
                    parse_mode='HTML'
                )
        else:
            await update.message.reply_text(message, parse_mode='HTML')

        # Also check if logs.md exists and send info
        logs_file = Path("/app/logs.md")
        if logs_file.exists():
            file_size = logs_file.stat().st_size
            await update.message.reply_text(
                f"ℹ️ Full logs are also written to <code>logs.md</code> ({file_size} bytes)\n"
                f"Updated every hour automatically.",
                parse_mode='HTML'
            )

    except Exception as e:
        logger.error(f"Error in logs command: {e}")
        await update.message.reply_text(f"❌ Error fetching logs: {e}")
