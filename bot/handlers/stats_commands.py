"""
Statistics Command Handlers
/stats - View bot statistics
/listpairs - Show all monitored pairs
"""

import logging
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
