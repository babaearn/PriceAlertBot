"""
Alert Checking Logic - Threshold Detection
"""

from datetime import date
from bot.services.database import (
    get_session_start_price,
    check_alert_fired,
    log_alert
)
from bot.config import GAINER_THRESHOLDS, LOSER_THRESHOLDS, MIN_VOLUME_24H
import logging

logger = logging.getLogger(__name__)


async def check_and_fire_alerts(pair_data, send_alert_callback):
    """
    Check if any thresholds are crossed and fire alerts

    Args:
        pair_data: Dict with symbol, current_price, volume_24h, adjust_link
        send_alert_callback: Async function to send alerts

    Returns: Number of alerts fired
    """
    symbol = pair_data['symbol']
    current_price = pair_data['current_price']
    volume_24h = pair_data['volume_24h']
    adjust_link = pair_data['adjust_link']

    # CRITICAL: Skip if no Adjust link
    if not adjust_link or adjust_link.strip() == '':
        logger.debug(f"⏭️ Skipping {symbol} - No Adjust link")
        return 0

    # CRITICAL: Skip if volume too low
    if volume_24h < MIN_VOLUME_24H:
        logger.debug(f"⏭️ Skipping {symbol} - Low volume: ${volume_24h:,.0f}")
        return 0

    # Get session start price (00:00 UTC)
    session_start_price = get_session_start_price(symbol)

    if not session_start_price:
        logger.warning(f"No session start price for {symbol}")
        return 0

    # Calculate % change from session start
    change_percent = ((current_price - session_start_price) / session_start_price) * 100

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

    # Fire alerts for new threshold crossings
    alerts_fired = 0
    today = date.today()

    for threshold in thresholds_crossed:
        if check_alert_fired(symbol, threshold, today):
            continue  # Already fired today

        try:
            # Send alert to Telegram
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
            logger.info(f"🚨 Alert fired: {symbol} {change_percent:+.1f}% (threshold: {threshold}%)")

        except Exception as e:
            logger.error(f"Alert send failed for {symbol}: {e}")

    return alerts_fired
