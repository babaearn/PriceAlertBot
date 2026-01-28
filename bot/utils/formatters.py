"""
Message Formatting and CTA Button Generation
"""

from telegram import InlineKeyboardButton, InlineKeyboardMarkup


def format_alert_message(symbol, current_price, session_start_price, change_percent):
    """
    Format alert message - clean design
    NO "Always DYOR before taking any trade" warning
    """
    clean_symbol = symbol.replace('/USDT', '')
    abs_change = abs(change_percent)
    is_gainer = change_percent > 0

    # Emoji and title based on % change
    if abs_change >= 400:
        emoji, title = "🔥💥🚀", "INSANE"
    elif abs_change >= 200:
        emoji, title = "🚀🔥", "MEGA"
    elif abs_change >= 100:
        emoji, title = "🚀", "HUGE"
    elif abs_change >= 60:
        emoji = "📈" if is_gainer else "📉"
        title = "BIG"
    elif abs_change >= 30:
        emoji = "⬆️" if is_gainer else "⬇️"
        title = "STRONG"
    else:
        emoji, title = "📊", "ALERT"

    move_type = "PUMP" if is_gainer else "DUMP"
    sign = "+" if is_gainer else ""

    # Price formatting
    if current_price < 0.01:
        price_fmt = f"${current_price:.6f}"
        start_fmt = f"${session_start_price:.6f}"
    elif current_price < 1:
        price_fmt = f"${current_price:.4f}"
        start_fmt = f"${session_start_price:.4f}"
    else:
        price_fmt = f"${current_price:,.2f}"
        start_fmt = f"${session_start_price:,.2f}"

    # Construct message - NO DYOR WARNING
    message = f"""
{emoji} <b>{title} {move_type}!</b> ({sign}{change_percent:.1f}%)

💰 <b>{clean_symbol}</b>
📊 {start_fmt} → {price_fmt}
📈 {sign}{change_percent:.2f}% (24h)
"""
    return message.strip()


def get_cta_button_text(symbol, change_percent):
    """Dynamic CTA button text based on % threshold"""
    clean_symbol = symbol.replace('/USDT', '')
    abs_change = abs(change_percent)

    if abs_change >= 100:
        return f"🔥 EXPLOSIVE GAINS - {clean_symbol}"
    elif abs_change >= 50:
        return f"🚀 DON'T MISS OUT - {clean_symbol}"
    elif abs_change >= 30:
        return f"📈 CATCH THE PUMP - {clean_symbol}"
    else:
        return f"💰 TRADE NOW - {clean_symbol}"


def create_single_cta_button(symbol, change_percent, adjust_link):
    """Create single CTA button - only ONE button per alert"""
    button_text = get_cta_button_text(symbol, change_percent)
    keyboard = [[InlineKeyboardButton(button_text, url=adjust_link)]]
    return InlineKeyboardMarkup(keyboard)


def format_pair_list(pairs):
    """Format list of pairs grouped by first letter"""
    if not pairs:
        return "No active pairs found."

    # Group by first letter
    grouped = {}
    for pair in pairs:
        symbol = pair['symbol']
        first_letter = symbol[0].upper()
        if first_letter not in grouped:
            grouped[first_letter] = []
        grouped[first_letter].append(symbol)

    # Format output
    lines = [f"📊 <b>Active Pairs ({len(pairs)} total)</b>\n"]

    for letter in sorted(grouped.keys()):
        symbols = sorted(grouped[letter])
        lines.append(f"<b>{letter}:</b> {', '.join([s.replace('/USDT', '') for s in symbols])}")

    return '\n'.join(lines)


def format_stats(stats):
    """Format statistics dashboard"""
    last_scan = stats.get('last_scan')

    message = f"""
📊 <b>Bot Statistics</b>

<b>Active Monitoring:</b>
• Pairs: {stats['active_pairs']}
• Min Volume: $5,000,000

<b>Alerts Fired:</b>
• Today: {stats['alerts_today']}
• Last 7 days: {stats['alerts_week']}
"""

    if last_scan:
        message += f"""
<b>Last Scan:</b>
• Cycle: #{last_scan['scan_cycle']}
• Pairs: {last_scan['pairs_scanned']}
• Alerts: {last_scan['alerts_triggered']}
• Errors: {last_scan['errors']}
• Duration: {last_scan['duration_seconds']:.2f}s
"""

    return message.strip()
