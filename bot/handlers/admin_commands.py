"""
Admin Command Handlers
/addnew - Add new trading pairs (single or bulk)
/removepair - Remove trading pair
/cooldown - Set alert cooldown
/turnoff - Toggle API sources
/automap - Auto-map symbols with Gemini AI (batch - 1 API call)
/ai - Toggle AI mode on/off
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
    Uses BATCH processing - all symbols in ONE API call (FREE tier friendly)
    Usage: /automap
    """
    user_id = update.effective_user.id

    # Check admin permission
    if not is_admin(user_id):
        await update.message.reply_text("❌ Access denied. Admin only.")
        return

    # Check if Gemini is available
    from bot.utils.gemini_symbol_resolver import is_gemini_available, batch_resolve_symbols

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
        f"🧠 <b>Starting Gemini 2.5 Flash mapping...</b>\n\n"
        f"📊 Processing {len(mudrex_symbols)} pairs\n"
        f"⏱️ ETA: 3-5 seconds (batch processing)\n"
        f"💰 Cost: FREE (1 API request)",
        parse_mode='HTML'
    )

    try:
        # Get Bybit symbols
        from bot.services.price_fetcher import PriceFetcher

        fetcher = PriceFetcher()
        bybit_markets = fetcher.bybit.load_markets()
        bybit_symbols = list(bybit_markets.keys())

        # Run Gemini BATCH mapping (all symbols in 1 API call)
        mappings = batch_resolve_symbols(mudrex_symbols, bybit_symbols)

        if not mappings:
            await update.message.reply_text("❌ Gemini failed. Check logs for details.")
            return

        # Save to AI cache
        from bot.utils.symbol_mapper import save_ai_cache

        save_ai_cache(mappings)

        # Calculate stats
        total = len(mappings)
        available = sum(1 for v in mappings.values() if v is not None)
        unavailable = sum(1 for v in mappings.values() if v is None)
        needs_mapping = sum(1 for k, v in mappings.items() if v and k != v)

        # Get sample mappings
        sample_lines = []
        count = 0
        for k, v in mappings.items():
            if count >= 5:
                break
            if v and k != v:
                sample_lines.append(f"  🔄 {k} → {v}")
                count += 1
            elif v is None:
                sample_lines.append(f"  ❌ {k}")
                count += 1

        sample_text = "\n".join(sample_lines) if sample_lines else "  (no mappings needed)"

        await update.message.reply_text(
            f"✅ <b>Gemini Mapping Complete!</b>\n\n"
            f"📊 <b>Results:</b>\n"
            f"• Total: {total}\n"
            f"• Available: {available} ({available/total*100:.1f}%)\n"
            f"• Unavailable: {unavailable}\n"
            f"• Mapped: {needs_mapping}\n\n"
            f"📝 <b>Sample:</b>\n"
            f"{sample_text}\n"
            f"... and {total - 5} more\n\n"
            f"💾 Saved to: /tmp/gemini_symbol_mappings.json\n"
            f"💡 Enable with: /ai on",
            parse_mode='HTML'
        )

    except Exception as e:
        logger.error(f"Error in automap command: {e}")
        await update.message.reply_text(f"❌ Error: {e}")


async def ai_toggle_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Toggle AI mode on/off
    Usage:
      /ai on  - Enable Gemini AI mappings
      /ai off - Use manual predefined mappings
      /ai status - Check current mode
    """
    user_id = update.effective_user.id

    # Check admin permission
    if not is_admin(user_id):
        await update.message.reply_text("❌ Access denied. Admin only.")
        return

    if not context.args:
        # Show current status
        ai_mode = get_config_value('ai_mode_enabled', 'false')
        mode_str = "🧠 AI Mode" if ai_mode == 'true' else "📖 Manual Mode"

        await update.message.reply_text(
            f"<b>Current Mode:</b> {mode_str}\n\n"
            f"<b>Usage:</b>\n"
            f"/ai on - Enable AI mappings\n"
            f"/ai off - Use manual mappings\n"
            f"/ai status - Check mode details",
            parse_mode='HTML'
        )
        return

    command = context.args[0].lower()

    if command == 'on':
        # Check if AI cache exists
        from bot.utils.symbol_mapper import get_ai_cache_stats

        cache_stats = get_ai_cache_stats()

        if cache_stats['loaded']:
            cache_status = f"✅ {cache_stats['count']} symbols cached"
        else:
            cache_status = "⚠️ No cache found, run /automap first"

        set_config_value('ai_mode_enabled', 'true', str(user_id))

        await update.message.reply_text(
            f"✅ <b>AI Mode Enabled</b>\n\n"
            f"🧠 Using Gemini 2.5 Flash mappings\n"
            f"📂 Cache: {cache_status}\n\n"
            f"💰 FREE tier: 20-50 requests/day\n"
            f"📊 Our usage: ~11 requests/month",
            parse_mode='HTML'
        )

    elif command == 'off':
        set_config_value('ai_mode_enabled', 'false', str(user_id))
        await update.message.reply_text(
            f"✅ <b>Manual Mode Enabled</b>\n\n"
            f"📖 Using predefined mappings\n"
            f"🔧 Edit symbol_mapper.py to add more\n\n"
            f"💡 Tip: Use /ai on for auto-mapping",
            parse_mode='HTML'
        )

    elif command == 'status':
        ai_mode = get_config_value('ai_mode_enabled', 'false')

        if ai_mode == 'true':
            from bot.utils.symbol_mapper import get_ai_cache_stats
            cache_stats = get_ai_cache_stats()

            if cache_stats['loaded']:
                await update.message.reply_text(
                    f"🧠 <b>AI Mode Active</b>\n\n"
                    f"📂 Cache: {cache_stats['count']} symbols\n"
                    f"✅ Available: {cache_stats['available']}\n"
                    f"❌ Unavailable: {cache_stats['unavailable']}\n"
                    f"🔄 Mapped: {cache_stats['mapped']}\n\n"
                    f"💰 Cost: FREE tier\n"
                    f"🔄 Run /automap to refresh",
                    parse_mode='HTML'
                )
            else:
                await update.message.reply_text(
                    f"🧠 <b>AI Mode Active</b>\n\n"
                    f"⚠️ No cache found\n"
                    f"🔧 Run /automap to generate",
                    parse_mode='HTML'
                )
        else:
            await update.message.reply_text(
                f"📖 <b>Manual Mode Active</b>\n\n"
                f"📝 Using predefined mappings\n"
                f"💡 Switch with /ai on",
                parse_mode='HTML'
            )

    else:
        await update.message.reply_text("❌ Use: /ai on, /ai off, or /ai status")


async def nativebybit_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Toggle native Bybit mode on/off
    Usage:
      /nativebybit on  - Monitor ALL Bybit pairs, find links with AI
      /nativebybit off - Use predefined pairs from database
    """
    user_id = update.effective_user.id

    # Check admin permission
    if not is_admin(user_id):
        await update.message.reply_text("❌ Access denied. Admin only.")
        return

    if not context.args:
        # Show current status
        mode = get_config_value('native_bybit_mode', 'false')
        mode_str = "Native Bybit (ALL pairs)" if mode == 'true' else "Predefined pairs (438)"

        await update.message.reply_text(
            f"<b>Current Scanner Mode:</b> {mode_str}\n\n"
            f"<b>Usage:</b>\n"
            f"/nativebybit on - Monitor ALL Bybit pairs\n"
            f"/nativebybit off - Use predefined 438 pairs",
            parse_mode='HTML'
        )
        return

    command = context.args[0].lower()

    if command == 'on':
        set_config_value('native_bybit_mode', 'true', str(user_id))
        await update.message.reply_text(
            f"<b>Native Bybit Mode Enabled</b>\n\n"
            f"Scanner will now monitor ALL Bybit USDT pairs\n"
            f"Adjust links found by AI when alerts fire\n\n"
            f"<b>Benefits:</b>\n"
            f"• 500+ pairs monitored\n"
            f"• Auto-detects new listings\n"
            f"• No manual symbol mapping\n\n"
            f"<b>Note:</b> GEMINI_API_KEY required for link finding",
            parse_mode='HTML'
        )

    elif command == 'off':
        set_config_value('native_bybit_mode', 'false', str(user_id))
        await update.message.reply_text(
            f"<b>Native Bybit Mode Disabled</b>\n\n"
            f"Scanner will use predefined 438 pairs\n"
            f"Using pre-loaded Adjust links\n\n"
            f"<b>Run /reseed</b> if pairs not loaded",
            parse_mode='HTML'
        )

    else:
        await update.message.reply_text("❌ Use: /nativebybit on or /nativebybit off")


async def seedlinks_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Seed known Adjust links from active_pairs to cache
    Gives AI better context for pattern matching
    Usage: /seedlinks
    """
    user_id = update.effective_user.id

    # Check admin permission
    if not is_admin(user_id):
        await update.message.reply_text("❌ Access denied. Admin only.")
        return

    await update.message.reply_text("Seeding known Adjust links to cache...")

    try:
        from bot.services.database import cache_adjust_link

        # Get all pairs with links
        pairs = get_active_pairs()

        seeded = 0
        for pair in pairs:
            symbol = pair['symbol']
            adjust_link = pair['adjust_link']

            if adjust_link and adjust_link.strip():
                cache_adjust_link(symbol, adjust_link, found_by='seed')
                seeded += 1

        await update.message.reply_text(
            f"<b>Seeding Complete!</b>\n\n"
            f"Loaded {seeded} Adjust links to cache\n"
            f"AI will use these for pattern matching\n\n"
            f"<b>Now you can:</b>\n"
            f"/nativebybit on - Enable native Bybit mode",
            parse_mode='HTML'
        )

    except Exception as e:
        logger.error(f"Error in seedlinks command: {e}")
        await update.message.reply_text(f"❌ Seeding failed: {e}")
