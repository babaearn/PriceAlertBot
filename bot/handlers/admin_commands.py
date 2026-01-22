"""
Admin Command Handlers
/addnew - Add new trading pairs (single or bulk)
/removepair - Remove trading pair
/cooldown - Set alert cooldown
"""

import logging
from telegram import Update
from telegram.ext import ContextTypes
from bot.utils.validators import is_admin, validate_symbol, validate_adjust_link, parse_cooldown
from bot.utils.helpers import parse_bulk_pairs
from bot.services.database import add_pair, remove_pair, set_config_value

logger = logging.getLogger(__name__)


async def addnew_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Add new trading pair(s)
    Usage:
      /addnew ELSA https://mudrex.go.link/elsa123
      /addnew ELSA link1 SKRU link2 SPORTFUN link3
    """
    user_id = update.effective_user.id

    # Check admin permission
    if not is_admin(user_id):
        await update.message.reply_text("❌ Access denied. Admin only.")
        return

    if not context.args or len(context.args) < 2:
        await update.message.reply_text(
            "❌ Invalid format.\n\n"
            "<b>Single pair:</b>\n"
            "/addnew SYMBOL https://mudrex.go.link/xyz\n\n"
            "<b>Bulk add:</b>\n"
            "/addnew ELSA link1 SKRU link2 SPORT link3",
            parse_mode='HTML'
        )
        return

    try:
        # Parse bulk pairs
        text = ' '.join(context.args)
        pairs = parse_bulk_pairs(text)

        added = []
        failed = []

        for symbol, link in pairs:
            # Validate symbol
            valid_symbol, result = validate_symbol(symbol)
            if not valid_symbol:
                failed.append(f"{symbol}: {result}")
                continue

            symbol = result

            # Validate Adjust link
            valid_link, result = validate_adjust_link(link)
            if not valid_link:
                failed.append(f"{symbol}: {result}")
                continue

            link = result

            # Add to database
            success = add_pair(symbol, link, str(user_id))

            if success:
                added.append(symbol)
            else:
                failed.append(f"{symbol}: Already exists")

        # Response
        response = []

        if added:
            response.append(f"✅ <b>Added {len(added)} pair(s):</b>")
            response.append(", ".join([s.replace('/USDT', '') for s in added]))

        if failed:
            response.append(f"\n❌ <b>Failed {len(failed)}:</b>")
            for error in failed:
                response.append(f"• {error}")

        await update.message.reply_text('\n'.join(response), parse_mode='HTML')

    except Exception as e:
        logger.error(f"Error in addnew command: {e}")
        await update.message.reply_text(f"❌ Error: {e}")


async def removepair_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Remove trading pair
    Usage: /removepair BTC/USDT
    """
    user_id = update.effective_user.id

    # Check admin permission
    if not is_admin(user_id):
        await update.message.reply_text("❌ Access denied. Admin only.")
        return

    if not context.args:
        await update.message.reply_text(
            "❌ Invalid format.\n\n"
            "Usage: /removepair SYMBOL\n"
            "Example: /removepair BTC",
            parse_mode='HTML'
        )
        return

    symbol = context.args[0].upper()

    # Auto-add /USDT if not present
    if '/' not in symbol:
        symbol = f"{symbol}/USDT"

    # Remove from database
    success = remove_pair(symbol)

    if success:
        await update.message.reply_text(f"✅ Removed: {symbol.replace('/USDT', '')}")
    else:
        await update.message.reply_text(f"❌ Pair not found: {symbol.replace('/USDT', '')}")


async def cooldown_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Set global alert cooldown
    Usage:
      /cooldown 30m
      /cooldown 1h
      /cooldown off
    """
    user_id = update.effective_user.id

    # Check admin permission
    if not is_admin(user_id):
        await update.message.reply_text("❌ Access denied. Admin only.")
        return

    if not context.args:
        await update.message.reply_text(
            "❌ Invalid format.\n\n"
            "Usage: /cooldown <time>\n\n"
            "Examples:\n"
            "• /cooldown 30m\n"
            "• /cooldown 1h\n"
            "• /cooldown off",
            parse_mode='HTML'
        )
        return

    cooldown_str = context.args[0]

    # Parse cooldown
    valid, minutes = parse_cooldown(cooldown_str)

    if not valid:
        await update.message.reply_text(
            f"❌ Invalid cooldown format: {cooldown_str}\n\n"
            "Valid formats: 30m, 1h, 2h30m, off"
        )
        return

    # Save to database
    set_config_value('cooldown_minutes', str(minutes), str(user_id))

    if minutes == 0:
        await update.message.reply_text("✅ Cooldown disabled")
    else:
        hours = minutes // 60
        mins = minutes % 60

        if hours > 0 and mins > 0:
            time_str = f"{hours}h {mins}m"
        elif hours > 0:
            time_str = f"{hours}h"
        else:
            time_str = f"{mins}m"

        await update.message.reply_text(f"✅ Cooldown set to: {time_str}")
