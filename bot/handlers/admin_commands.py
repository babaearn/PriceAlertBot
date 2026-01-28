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


def format_volume(volume: float) -> str:
    """Format volume in human-readable format"""
    if volume >= 1_000_000_000:
        return f"${volume/1_000_000_000:.1f}B"
    elif volume >= 1_000_000:
        return f"${volume/1_000_000:.1f}M"
    elif volume >= 1_000:
        return f"${volume/1_000:.1f}K"
    else:
        return f"${volume:.0f}"


async def volume_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Set minimum volume threshold
    Usage: /volume <amount> or /volume 5M or /volume reset
    """
    user_id = update.effective_user.id

    if not is_admin(user_id):
        await update.message.reply_text("❌ Access denied. Admin only.")
        return

    args = context.args

    # Show current setting
    if not args:
        current = int(get_config_value('min_volume_usd', '5000000'))
        await update.message.reply_text(
            f"📊 <b>Current Volume Threshold</b>\n\n"
            f"💰 ${current:,.0f}\n"
            f"({format_volume(current)})\n\n"
            f"💡 Usage: <code>/volume 10M</code> or <code>/volume 5000000</code>",
            parse_mode='HTML'
        )
        return

    value_str = args[0].upper()

    # Reset to default
    if value_str == 'RESET':
        new_volume = 5_000_000
        set_config_value('min_volume_usd', str(new_volume), str(user_id))
        await update.message.reply_text(
            f"🔄 <b>Volume Threshold Reset</b>\n\n"
            f"💰 ${new_volume:,.0f} (Default)\n\n"
            f"✅ Takes effect on next scan",
            parse_mode='HTML'
        )
        return

    # Parse value
    try:
        if value_str.endswith('B'):
            new_volume = int(float(value_str[:-1]) * 1_000_000_000)
        elif value_str.endswith('M'):
            new_volume = int(float(value_str[:-1]) * 1_000_000)
        elif value_str.endswith('K'):
            new_volume = int(float(value_str[:-1]) * 1_000)
        else:
            new_volume = int(value_str)

        # Validate range
        if new_volume < 100_000:
            await update.message.reply_text(
                "❌ <b>Too Low</b>\n\n"
                "Minimum: $100,000 (100K)\n"
                "This prevents tracking too many low-volume pairs",
                parse_mode='HTML'
            )
            return

        if new_volume > 10_000_000_000:
            await update.message.reply_text(
                "❌ <b>Too High</b>\n\n"
                "Maximum: $10,000,000,000 (10B)\n"
                "This would filter out almost all pairs",
                parse_mode='HTML'
            )
            return

        # Get old value
        old_volume = int(get_config_value('min_volume_usd', '5000000'))

        # Update setting
        set_config_value('min_volume_usd', str(new_volume), str(user_id))

        await update.message.reply_text(
            f"✅ <b>Volume Threshold Updated</b>\n\n"
            f"Old: ${old_volume:,.0f}\n"
            f"New: ${new_volume:,.0f}\n\n"
            f"⏱️ Takes effect on next scan",
            parse_mode='HTML'
        )

    except ValueError:
        await update.message.reply_text(
            "❌ <b>Invalid Format</b>\n\n"
            "Examples:\n"
            "• <code>/volume 5000000</code>\n"
            "• <code>/volume 5M</code>\n"
            "• <code>/volume 1.5B</code>\n"
            "• <code>/volume reset</code>",
            parse_mode='HTML'
        )


async def interval_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Change scan interval
    Usage: /interval 30s or /interval 1m
    """
    user_id = update.effective_user.id

    if not is_admin(user_id):
        await update.message.reply_text("❌ Access denied. Admin only.")
        return

    args = context.args

    # Show current setting
    if not args:
        from bot import config
        current = int(get_config_value('scan_interval_seconds', str(config.SCAN_INTERVAL)))
        scans_per_hour = 3600 // current

        await update.message.reply_text(
            f"⏱️ <b>Current Scan Interval</b>\n\n"
            f"🔄 {current} seconds\n\n"
            f"📊 <b>Stats:</b>\n"
            f"• Scans/hour: {scans_per_hour}\n"
            f"• Scans/day: {scans_per_hour * 24:,}\n\n"
            f"💡 Usage: <code>/interval 15s</code> or <code>/interval 1m</code>",
            parse_mode='HTML'
        )
        return

    value_str = args[0].upper()

    # Reset
    if value_str == 'RESET':
        from bot.handlers import control_commands
        new_interval = 30
        set_config_value('scan_interval_seconds', str(new_interval), str(user_id))

        # Apply immediately if monitor is available
        applied_live = False
        if control_commands.price_monitor:
            try:
                applied_live = control_commands.price_monitor.update_interval(new_interval)
            except Exception as e:
                logger.error(f"Failed to apply interval live: {e}")

        status_msg = "✅ Applied immediately" if applied_live else "⚠️ Restart bot to apply"

        await update.message.reply_text(
            f"🔄 <b>Scan Interval Reset</b>\n\n"
            f"⏱️ {new_interval} seconds (Default)\n\n"
            f"{status_msg}",
            parse_mode='HTML'
        )
        return

    # Parse interval
    try:
        if value_str.endswith('S'):
            new_interval = int(value_str[:-1])
        elif value_str.endswith('M'):
            new_interval = int(float(value_str[:-1]) * 60)
        else:
            new_interval = int(value_str)

        # Validate
        if new_interval < 5:
            await update.message.reply_text(
                "❌ <b>Too Fast</b>\n\n"
                "Minimum: 5 seconds\n\n"
                "⚠️ Going below 5s may cause API issues",
                parse_mode='HTML'
            )
            return

        if new_interval > 300:
            await update.message.reply_text(
                "❌ <b>Too Slow</b>\n\n"
                "Maximum: 300 seconds (5 minutes)",
                parse_mode='HTML'
            )
            return

        # Get old value
        from bot import config
        from bot.handlers import control_commands
        old_interval = int(get_config_value('scan_interval_seconds', str(config.SCAN_INTERVAL)))

        # Update setting in database
        set_config_value('scan_interval_seconds', str(new_interval), str(user_id))

        # Apply immediately if monitor is available
        applied_live = False
        if control_commands.price_monitor:
            try:
                applied_live = control_commands.price_monitor.update_interval(new_interval)
            except Exception as e:
                logger.error(f"Failed to apply interval live: {e}")

        old_scans = 3600 // old_interval
        new_scans = 3600 // new_interval
        change_pct = ((new_scans - old_scans) / old_scans * 100) if old_scans > 0 else 0

        status_msg = "✅ Applied immediately - No restart needed!" if applied_live else "⚠️ Restart bot to apply"

        await update.message.reply_text(
            f"✅ <b>Scan Interval Updated</b>\n\n"
            f"Old: {old_interval} seconds\n"
            f"New: {new_interval} seconds\n\n"
            f"📊 <b>Impact:</b>\n"
            f"• Scans/hour: {old_scans} → {new_scans} ({change_pct:+.0f}%)\n\n"
            f"{status_msg}",
            parse_mode='HTML'
        )

    except ValueError:
        await update.message.reply_text(
            "❌ <b>Invalid Format</b>\n\n"
            "Examples:\n"
            "• <code>/interval 30s</code>\n"
            "• <code>/interval 1m</code>\n"
            "• <code>/interval 15s</code>\n"
            "• <code>/interval reset</code>",
            parse_mode='HTML'
        )


async def show_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Show currently monitored pairs
    /show - Show filtered pairs (meeting volume threshold)
    /show all - Show all available Bybit USDT pairs
    /show stats - Show detailed statistics
    """
    user_id = update.effective_user.id

    if not is_admin(user_id):
        await update.message.reply_text("❌ Access denied. Admin only.")
        return

    args = context.args
    mode = args[0].lower() if args else 'filtered'

    await update.message.reply_text("🔄 Fetching market data...")

    try:
        from bot.services.price_fetcher import PriceFetcher
        from bot import config

        # Get current settings
        min_volume = int(get_config_value('min_volume_usd', str(config.MIN_VOLUME_24H)))

        # Fetch current market data
        fetcher = PriceFetcher()
        all_tickers = fetcher.bybit.fetch_tickers()

        # Filter USDT pairs
        usdt_pairs = {
            symbol: ticker for symbol, ticker in all_tickers.items()
            if symbol.endswith('/USDT')
        }

        # Sort by volume
        sorted_pairs = sorted(
            usdt_pairs.items(),
            key=lambda x: float(x[1].get('quoteVolume', 0) or 0),
            reverse=True
        )

        # Separate qualified vs unqualified
        qualified = []
        for symbol, ticker in sorted_pairs:
            volume = float(ticker.get('quoteVolume', 0) or 0)
            if volume >= min_volume:
                qualified.append((symbol, volume))

        # MODE: Filtered (default) - show only qualified pairs
        if mode == 'filtered':
            if not qualified:
                await update.message.reply_text(
                    f"📊 <b>No pairs meet threshold</b>\n\n"
                    f"Volume threshold: {format_volume(min_volume)}\n"
                    f"Total pairs on Bybit: {len(usdt_pairs)}\n\n"
                    f"💡 Try lowering threshold: <code>/volume 1M</code>",
                    parse_mode='HTML'
                )
                return

            # Show qualified pairs (max 30)
            display_pairs = qualified[:30]
            pairs_list = "\n".join([
                f"{i+1}. {symbol:14} {format_volume(vol)}"
                for i, (symbol, vol) in enumerate(display_pairs)
            ])

            more_text = f"\n... and {len(qualified) - 30} more" if len(qualified) > 30 else ""

            await update.message.reply_text(
                f"📊 <b>Filtered Pairs</b> (Volume ≥ {format_volume(min_volume)})\n\n"
                f"✅ <b>{len(qualified)} pairs qualified:</b>\n\n"
                f"<code>{pairs_list}</code>{more_text}\n\n"
                f"💡 <code>/show all</code> - See all {len(usdt_pairs)} pairs\n"
                f"💡 <code>/volume 10M</code> - Change threshold",
                parse_mode='HTML'
            )

        # MODE: All pairs
        elif mode == 'all':
            # Show all pairs (max 50)
            display_pairs = sorted_pairs[:50]
            pairs_list = "\n".join([
                f"{i+1}. {symbol:14} {format_volume(float(ticker.get('quoteVolume', 0) or 0))} {'✅' if float(ticker.get('quoteVolume', 0) or 0) >= min_volume else '❌'}"
                for i, (symbol, ticker) in enumerate(display_pairs)
            ])

            await update.message.reply_text(
                f"📊 <b>All Bybit USDT Pairs</b>\n\n"
                f"Total: {len(usdt_pairs)} pairs\n"
                f"Qualified (≥{format_volume(min_volume)}): {len(qualified)}\n\n"
                f"<b>Top 50 by volume:</b>\n"
                f"<code>{pairs_list}</code>\n"
                f"... and {len(usdt_pairs) - 50} more\n\n"
                f"✅ = Meets volume threshold\n"
                f"❌ = Below threshold",
                parse_mode='HTML'
            )

        # MODE: Stats
        elif mode == 'stats':
            total_volume = sum(vol for _, vol in qualified) if qualified else 0
            avg_volume = total_volume / len(qualified) if qualified else 0

            # Volume distribution
            mega = sum(1 for _, vol in qualified if vol >= 100_000_000)
            large = sum(1 for _, vol in qualified if 50_000_000 <= vol < 100_000_000)
            mid = sum(1 for _, vol in qualified if 10_000_000 <= vol < 50_000_000)
            small = sum(1 for _, vol in qualified if vol < 10_000_000)

            await update.message.reply_text(
                f"📊 <b>Detailed Statistics</b>\n\n"
                f"<b>Filter:</b> {format_volume(min_volume)}\n"
                f"<b>Total on Bybit:</b> {len(usdt_pairs)}\n"
                f"<b>Qualified:</b> {len(qualified)} ({len(qualified)/len(usdt_pairs)*100:.1f}%)\n\n"
                f"<b>Volume Breakdown:</b>\n"
                f"• Mega (≥$100M): {mega}\n"
                f"• Large ($50M-$100M): {large}\n"
                f"• Mid ($10M-$50M): {mid}\n"
                f"• Small (&lt;$10M): {small}\n\n"
                f"<b>Volume Stats:</b>\n"
                f"• Total: {format_volume(total_volume)}\n"
                f"• Average: {format_volume(avg_volume)}\n"
                f"• Highest: {format_volume(qualified[0][1]) if qualified else 0}\n"
                f"• Lowest: {format_volume(qualified[-1][1]) if qualified else 0}",
                parse_mode='HTML'
            )

        else:
            await update.message.reply_text(
                "❌ <b>Invalid option</b>\n\n"
                "Usage:\n"
                "• <code>/show</code> - Filtered pairs only\n"
                "• <code>/show all</code> - All Bybit pairs\n"
                "• <code>/show stats</code> - Detailed statistics",
                parse_mode='HTML'
            )

    except Exception as e:
        logger.error(f"Error in show command: {e}")
        await update.message.reply_text(f"❌ Error: {e}")


async def resetsession_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Manually reset session to current prices
    Usage: /resetsession

    This sets all session start prices to CURRENT prices,
    effectively resetting the baseline for % change calculations.
    Also clears today's alert history so alerts can fire again.
    """
    user_id = update.effective_user.id

    if not is_admin(user_id):
        await update.message.reply_text("❌ Access denied. Admin only.")
        return

    await update.message.reply_text("🔄 <b>Resetting session...</b>\n\nThis may take a few seconds.", parse_mode='HTML')

    try:
        from bot.services.session_manager import reset_session_full

        # Full reset
        synced = await reset_session_full()

        if synced > 0:
            await update.message.reply_text(
                f"✅ <b>Session Reset Complete!</b>\n\n"
                f"📊 {synced} pairs synced to current prices\n"
                f"🗑️ Today's alert history cleared\n\n"
                f"⏱️ Next scan will compare to these new baseline prices\n"
                f"📈 Alerts will fire when prices move ±10% from now",
                parse_mode='HTML'
            )
        else:
            await update.message.reply_text("❌ Session reset failed. Check logs for details.")

    except Exception as e:
        logger.error(f"Error in resetsession command: {e}")
        await update.message.reply_text(f"❌ Reset failed: {e}")


async def syncprices_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Sync session prices (info command)
    Usage: /syncprices
    """
    user_id = update.effective_user.id

    if not is_admin(user_id):
        await update.message.reply_text("❌ Access denied. Admin only.")
        return

    await update.message.reply_text(
        "ℹ️ <b>Session Price Sync</b>\n\n"
        "<b>How it works:</b>\n"
        "• Session prices are set when bot starts\n"
        "• They reset automatically at 00:00 UTC\n"
        "• % changes are calculated from session start\n\n"
        "<b>After Deployment:</b>\n"
        "Session prices are set to current market prices.\n"
        "Alerts will fire when prices move ±10% from that point.\n\n"
        "<b>Manual Reset:</b>\n"
        "Use <code>/resetsession</code> to:\n"
        "• Reset all prices to current values\n"
        "• Clear today's alert history\n"
        "• Allow alerts to fire again\n\n"
        "<b>💡 Best Practice:</b>\n"
        "Keep bot running 24/7 to capture true 00:00 UTC prices!",
        parse_mode='HTML'
    )


async def testalert_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Send a test alert to verify bot is working
    Usage: /testalert
    """
    user_id = update.effective_user.id

    if not is_admin(user_id):
        await update.message.reply_text("❌ Access denied. Admin only.")
        return

    try:
        from bot.utils.formatters import format_alert_message, create_single_cta_button
        from bot import config

        # Create test alert
        test_symbol = "TEST/USDT"
        test_price = 1.2345
        test_session_price = 1.0000
        test_change = 23.45

        message = format_alert_message(
            test_symbol,
            test_price,
            test_session_price,
            test_change
        )

        button = create_single_cta_button(test_symbol, test_change, "https://mudrex.go.link/test")

        # Send to current chat
        await update.message.reply_text(
            f"🧪 <b>TEST ALERT</b>\n\n{message}",
            parse_mode='HTML',
            reply_markup=button
        )

        await update.message.reply_text(
            "✅ Test alert sent!\n\n"
            "If you see the alert above with the CTA button, "
            "the bot is working correctly."
        )

    except Exception as e:
        logger.error(f"Error in testalert command: {e}")
        await update.message.reply_text(f"❌ Test failed: {e}")
