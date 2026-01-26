"""
Admin Command Handlers
/addnew - Add new trading pairs (single or bulk)
/removepair - Remove trading pair
/cooldown - Set alert cooldown
/turnoff - Toggle API sources
/automap - Auto-map symbols with Gemini AI
"""

import logging
from telegram import Update
from telegram.ext import ContextTypes
from bot.utils.validators import is_admin, validate_symbol, validate_adjust_link, parse_cooldown
from bot.utils.helpers import parse_bulk_pairs
from bot.services.database import add_pair, remove_pair, set_config_value, get_config_value, seed_initial_pairs, get_active_pairs

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


async def reseed_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Force reseed all trading pairs
    Usage: /reseed
    WARNING: This will clear all existing pairs and reload from seed data
    """
    user_id = update.effective_user.id

    # Check admin permission
    if not is_admin(user_id):
        await update.message.reply_text("❌ Access denied. Admin only.")
        return

    await update.message.reply_text("🔄 <b>Reseeding database...</b>\nThis will clear existing pairs and reload 438 pairs.", parse_mode='HTML')

    try:
        # Force reseed
        count = seed_initial_pairs(force_reseed=True)

        if count > 0:
            await update.message.reply_text(
                f"✅ <b>Reseed complete!</b>\n\n"
                f"Loaded <b>{count}</b> trading pairs with Adjust links.\n\n"
                f"Run /test to verify.",
                parse_mode='HTML'
            )
        else:
            await update.message.reply_text("❌ Reseed failed. Check logs for details.")

    except Exception as e:
        logger.error(f"Error in reseed command: {e}")
        await update.message.reply_text(f"❌ Error: {e}")


async def turnoff_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Toggle API sources on/off
    Usage:
      /turnoff binance - Disable Binance, use only Bybit
      /turnoff bybit - Disable Bybit, use only Binance
      /turnoff none - Enable both APIs (default)
    """
    user_id = update.effective_user.id

    # Check admin permission
    if not is_admin(user_id):
        await update.message.reply_text("❌ Access denied. Admin only.")
        return

    if not context.args:
        # Show current status
        bybit_status = get_config_value('api_bybit_enabled', 'true')
        binance_status = get_config_value('api_binance_enabled', 'true')

        await update.message.reply_text(
            "🔧 <b>API Toggle Settings</b>\n\n"
            f"🔵 Bybit: {'✅ Enabled' if bybit_status == 'true' else '❌ Disabled'}\n"
            f"🟡 Binance: {'✅ Enabled' if binance_status == 'true' else '❌ Disabled'}\n\n"
            "<b>Usage:</b>\n"
            "/turnoff binance - Use only Bybit\n"
            "/turnoff bybit - Use only Binance\n"
            "/turnoff none - Enable both (default)",
            parse_mode='HTML'
        )
        return

    target = context.args[0].lower()

    if target == 'binance':
        set_config_value('api_bybit_enabled', 'true', str(user_id))
        set_config_value('api_binance_enabled', 'false', str(user_id))
        await update.message.reply_text(
            "✅ <b>Binance API disabled</b>\n\n"
            "🔵 Using ONLY Bybit for price data\n"
            "⚠️ If Bybit fails, no fallback available",
            parse_mode='HTML'
        )

    elif target == 'bybit':
        set_config_value('api_bybit_enabled', 'false', str(user_id))
        set_config_value('api_binance_enabled', 'true', str(user_id))
        await update.message.reply_text(
            "✅ <b>Bybit API disabled</b>\n\n"
            "🟡 Using ONLY Binance for price data\n"
            "⚠️ Not recommended - Bybit has more pairs",
            parse_mode='HTML'
        )

    elif target == 'none':
        set_config_value('api_bybit_enabled', 'true', str(user_id))
        set_config_value('api_binance_enabled', 'true', str(user_id))
        await update.message.reply_text(
            "✅ <b>Both APIs enabled</b>\n\n"
            "🔵 Primary: Bybit\n"
            "🟡 Fallback: Binance",
            parse_mode='HTML'
        )

    else:
        await update.message.reply_text(
            "❌ Invalid option.\n\n"
            "Valid options: binance, bybit, none"
        )


async def automap_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Use Gemini AI to automatically map all Mudrex symbols to Bybit
    Usage: /automap
    """
    user_id = update.effective_user.id

    # Check admin permission
    if not is_admin(user_id):
        await update.message.reply_text("❌ Access denied. Admin only.")
        return

    # Check if Gemini is available
    from bot.utils.gemini_resolver import is_gemini_available, auto_generate_mappings

    if not is_gemini_available():
        await update.message.reply_text(
            "❌ <b>Gemini API not configured</b>\n\n"
            "Add GEMINI_API_KEY to your environment variables.\n"
            "Get your key at: https://aistudio.google.com/app/apikey",
            parse_mode='HTML'
        )
        return

    # Get Mudrex symbols
    pairs = get_active_pairs()
    mudrex_symbols = [p['symbol'] for p in pairs]

    await update.message.reply_text(
        f"🧠 <b>Starting Gemini auto-mapping...</b>\n\n"
        f"📊 Processing {len(mudrex_symbols)} pairs\n"
        f"⏱️ Estimated time: ~{len(mudrex_symbols) // 60 + 1} minutes\n"
        f"(1 second per symbol for rate limiting)",
        parse_mode='HTML'
    )

    try:
        # Get Bybit symbols
        from bot.services.price_fetcher import PriceFetcher

        fetcher = PriceFetcher()
        bybit_markets = fetcher.bybit.load_markets()
        bybit_symbols = list(bybit_markets.keys())

        # Run Gemini auto-mapping
        mappings = auto_generate_mappings(mudrex_symbols, bybit_symbols)

        # Update symbol mapper with results
        from bot.utils.symbol_mapper import add_mapping

        changed = 0
        unavailable = 0

        for mudrex_sym, bybit_sym in mappings.items():
            if bybit_sym is None:
                unavailable += 1
                add_mapping(mudrex_sym, None)
            elif mudrex_sym != bybit_sym:
                changed += 1
                add_mapping(mudrex_sym, bybit_sym)

        available = len(mappings) - unavailable

        await update.message.reply_text(
            f"✅ <b>Gemini auto-mapping complete!</b>\n\n"
            f"📊 <b>Results:</b>\n"
            f"• Total pairs: {len(mappings)}\n"
            f"• Available on Bybit: {available}\n"
            f"• Needs mapping: {changed}\n"
            f"• Unavailable: {unavailable}\n\n"
            f"🔄 Mappings have been applied to the current session.\n"
            f"Run /test to verify.",
            parse_mode='HTML'
        )

    except Exception as e:
        logger.error(f"Error in automap command: {e}")
        await update.message.reply_text(f"❌ Error: {e}")
