"""
Alert Checking Logic - Threshold Detection with AI Link Finding
"""

from datetime import date
import logging
from bot.services.database import (
    get_session_start_price,
    save_session_start_price,
    check_alert_fired,
    log_alert
)
from bot.config import GAINER_THRESHOLDS, LOSER_THRESHOLDS, MIN_VOLUME_24H

logger = logging.getLogger(__name__)


async def check_and_fire_alerts_with_ai(pair_data: dict, send_alert_callback) -> int:
    """
    Check thresholds and fire alerts with AI-powered Adjust link discovery

    Args:
        pair_data: {symbol, current_price, volume_24h}
        send_alert_callback: Async function to send alerts

    Returns:
        Number of alerts fired
    """
    symbol = pair_data['symbol']
    current_price = pair_data['current_price']
    volume_24h = pair_data['volume_24h']

    # Skip low volume (already checked in scanner, but double-check)
    if volume_24h < MIN_VOLUME_24H:
        return 0

    # Get session start price (00:00 UTC)
    session_start_price = get_session_start_price(symbol)

    if not session_start_price:
        # First time seeing this pair, save current price as session start
        save_session_start_price(symbol, current_price)
        return 0

    # Calculate % change from session start
    change_percent = ((current_price - session_start_price) / session_start_price) * 100

    # Quick check - skip if change is too small
    min_threshold = min(GAINER_THRESHOLDS[0] if GAINER_THRESHOLDS else 100,
                        abs(LOSER_THRESHOLDS[0]) if LOSER_THRESHOLDS else 100)
    if abs(change_percent) < min_threshold:
        return 0

    # Find crossed thresholds
    thresholds_crossed = []

    if change_percent > 0:
        for threshold in GAINER_THRESHOLDS:
            if change_percent >= threshold:
                thresholds_crossed.append(threshold)
    else:
        for threshold in LOSER_THRESHOLDS:
            if change_percent <= threshold:
                thresholds_crossed.append(threshold)

    if not thresholds_crossed:
        return 0

    # Fire alerts for new threshold crossings
    alerts_fired = 0
    today = date.today()

    for threshold in thresholds_crossed:
        # Skip if already fired today
        if check_alert_fired(symbol, threshold, today):
            continue

        # AI: Find Adjust link (with caching)
        from bot.services.adjust_link_finder import find_adjust_link_with_ai
        adjust_link = await find_adjust_link_with_ai(symbol)

        if not adjust_link:
            logger.debug(f"Skipping {symbol}: No Adjust link")
            continue

        try:
            # Send alert
            message_id = await send_alert_callback(
                symbol=symbol,
                current_price=current_price,
                session_start_price=session_start_price,
                change_percent=change_percent,
                adjust_link=adjust_link
            )

            # Log to database
            log_alert(
                symbol=symbol,
                threshold_percent=threshold,
                trigger_price=current_price,
                session_start_price=session_start_price,
                actual_change_percent=change_percent,
                volume_24h=volume_24h,
                telegram_message_id=message_id,
                session_date=today
            )

            alerts_fired += 1
            logger.info(f"Alert: {symbol} {change_percent:+.1f}% (threshold: {threshold}%)")

        except Exception as e:
            logger.error(f"Alert failed for {symbol}: {e}")

    return alerts_fired
