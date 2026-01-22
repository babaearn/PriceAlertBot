"""
Input Validation Utilities
"""

import re
from typing import Tuple


def validate_symbol(symbol: str) -> Tuple[bool, str]:
    """
    Validate trading pair symbol format
    Returns: (is_valid, error_message)
    """
    if not symbol:
        return False, "Symbol cannot be empty"

    # Auto-add /USDT if not present
    if '/' not in symbol:
        symbol = f"{symbol.upper()}/USDT"
    else:
        symbol = symbol.upper()

    # Check format: ABC/USDT
    pattern = r'^[A-Z0-9]+/USDT$'
    if not re.match(pattern, symbol):
        return False, f"Invalid symbol format: {symbol}. Expected format: BTC/USDT"

    return True, symbol


def validate_adjust_link(link: str) -> Tuple[bool, str]:
    """
    Validate Adjust deeplink URL
    Returns: (is_valid, error_message)
    """
    if not link:
        return False, "Adjust link cannot be empty"

    link = link.strip()

    # Check if it's a valid URL
    if not link.startswith('http'):
        return False, f"Invalid URL: {link}. Must start with http:// or https://"

    # Common Adjust domains
    valid_domains = ['mudrex.go.link', 'adjust.com', 'app.adjust.com']

    if not any(domain in link for domain in valid_domains):
        return False, f"Link must be from a valid Adjust domain: {', '.join(valid_domains)}"

    return True, link


def parse_cooldown(cooldown_str: str) -> Tuple[bool, int]:
    """
    Parse cooldown string to minutes
    Examples: "30m", "1h", "2h30m", "off"
    Returns: (is_valid, minutes)
    """
    cooldown_str = cooldown_str.lower().strip()

    if cooldown_str in ['off', '0', 'disable', 'disabled']:
        return True, 0

    # Parse patterns like "30m", "1h", "2h30m"
    total_minutes = 0

    # Hours
    hours_match = re.search(r'(\d+)h', cooldown_str)
    if hours_match:
        total_minutes += int(hours_match.group(1)) * 60

    # Minutes
    minutes_match = re.search(r'(\d+)m', cooldown_str)
    if minutes_match:
        total_minutes += int(minutes_match.group(1))

    if total_minutes > 0:
        return True, total_minutes

    return False, 0


def is_admin(user_id: int) -> bool:
    """Check if user is admin"""
    from bot.config import ADMIN_USER_IDS
    return user_id in ADMIN_USER_IDS
