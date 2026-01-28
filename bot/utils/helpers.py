"""
General Helper Functions
"""

from datetime import datetime


def get_current_utc_time():
    """Get current UTC time"""
    return datetime.utcnow()


def format_number(num, decimals=2):
    """Format number with commas and decimals"""
    return f"{num:,.{decimals}f}"


def format_currency(amount, decimals=2):
    """Format currency with $ sign"""
    return f"${format_number(amount, decimals)}"


def truncate_text(text, max_length=100):
    """Truncate text to max length"""
    if len(text) <= max_length:
        return text
    return text[:max_length - 3] + "..."


def parse_bulk_pairs(text: str):
    """
    Parse bulk pair input
    Format: "SYMBOL1 link1 SYMBOL2 link2 SYMBOL3 link3"
    Returns: List of (symbol, link) tuples
    """
    parts = text.split()

    if len(parts) % 2 != 0:
        raise ValueError("Invalid format. Expected: SYMBOL1 link1 SYMBOL2 link2")

    pairs = []
    for i in range(0, len(parts), 2):
        symbol = parts[i].upper()
        link = parts[i + 1]

        # Auto-add /USDT if not present
        if '/' not in symbol:
            symbol = f"{symbol}/USDT"

        pairs.append((symbol, link))

    return pairs


def get_threshold_emoji(change_percent):
    """Get emoji based on % change"""
    abs_change = abs(change_percent)

    if abs_change >= 400:
        return "🔥💥🚀"
    elif abs_change >= 200:
        return "🚀🔥"
    elif abs_change >= 100:
        return "🚀"
    elif abs_change >= 60:
        return "📈" if change_percent > 0 else "📉"
    elif abs_change >= 30:
        return "⬆️" if change_percent > 0 else "⬇️"
    else:
        return "📊"
