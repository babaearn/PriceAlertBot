"""
Price Monitoring Service - Background Scanner with APScheduler
"""

import asyncio
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from bot.services.price_fetcher import PriceFetcher
from bot.services.alert_checker import check_and_fire_alerts
from bot.services.session_manager import SessionManager
from bot.services.database import get_active_pairs, log_scan_cycle, save_price_snapshot
from bot.config import SCAN_INTERVAL, BATCH_SIZE, TELEGRAM_GROUP_ID, PRICE_ALERTS_TOPIC_ID
import logging
import time

logger = logging.getLogger(__name__)


class PriceMonitor:
    """
    Background price monitoring service using REST API
    Runs every SCAN_INTERVAL seconds (default: 30s)
    """

    def __init__(self, bot_instance):
        self.bot = bot_instance
        self.fetcher = PriceFetcher()
        self.session_manager = SessionManager()
        self.scheduler = AsyncIOScheduler()
        self.scan_count = 0
        self.is_running = True

    async def scan_prices(self):
        """Main scanning loop - runs every 30 seconds"""
        if not self.is_running:
            logger.debug("Scanner paused, skipping scan")
            return

        start_time = time.time()
        self.scan_count += 1

        try:
            # Check for session reset (00:00 UTC)
            if self.session_manager.check_and_reset_session():
                logger.info("✅ Daily session reset complete")

            # Get all active pairs with Adjust links
            active_pairs = get_active_pairs()

            if not active_pairs:
                logger.warning("No active pairs to monitor")
                return

            logger.info(f"Scan #{self.scan_count}: Checking {len(active_pairs)} pairs")

            # Split into batches for API efficiency
            batches = [
                active_pairs[i:i + BATCH_SIZE]
                for i in range(0, len(active_pairs), BATCH_SIZE)
            ]

            total_alerts = 0
            total_checked = 0
            errors = 0

            for batch_idx, batch in enumerate(batches, 1):
                try:
                    symbols = [pair['symbol'] for pair in batch]

                    # Fetch prices for batch (REST API)
                    prices = self.fetcher.fetch_batch_prices(symbols)

                    # Check alerts for each pair in batch
                    for pair in batch:
                        symbol = pair['symbol']

                        if symbol not in prices:
                            logger.warning(f"No price data for {symbol}")
                            errors += 1
                            continue

                        price_data = prices[symbol]

                        # Get session start price for this symbol
                        from bot.services.database import get_session_start_price
                        session_start = get_session_start_price(symbol)

                        # If no session start price, use current price as baseline
                        if not session_start:
                            session_start = price_data['price']

                        # Save price snapshot
                        save_price_snapshot(
                            symbol=symbol,
                            price=price_data['price'],
                            volume_24h=price_data['volume_24h'],
                            session_start_price=session_start,
                            source=price_data['source']
                        )

                        pair_data = {
                            'symbol': symbol,
                            'current_price': price_data['price'],
                            'volume_24h': price_data['volume_24h'],
                            'adjust_link': pair['adjust_link']
                        }

                        # Check and fire alerts if thresholds crossed
                        alerts = await check_and_fire_alerts(
                            pair_data,
                            self.send_alert
                        )

                        total_alerts += alerts
                        total_checked += 1

                    # Small delay between batches
                    if batch_idx < len(batches):
                        await asyncio.sleep(0.5)

                except Exception as e:
                    logger.error(f"Batch {batch_idx} error: {e}")
                    errors += 1

            # Log scan results
            duration = time.time() - start_time
            log_scan_cycle(self.scan_count, total_checked, total_alerts, errors, duration)

            logger.info(
                f"✅ Scan #{self.scan_count} complete: "
                f"{total_checked} pairs, {total_alerts} alerts, "
                f"{errors} errors, {duration:.2f}s"
            )

        except Exception as e:
            logger.error(f"Scan error: {e}")

    async def send_alert(self, symbol, current_price, session_start_price,
                        change_percent, adjust_link):
        """Send alert to Telegram group"""
        from bot.utils.formatters import format_alert_message, create_single_cta_button

        try:
            message = format_alert_message(
                symbol,
                current_price,
                session_start_price,
                change_percent
            )

            button = create_single_cta_button(symbol, change_percent, adjust_link)

            sent_message = await self.bot.send_message(
                chat_id=TELEGRAM_GROUP_ID,
                message_thread_id=PRICE_ALERTS_TOPIC_ID,
                text=message,
                parse_mode='HTML',
                reply_markup=button
            )

            return sent_message.message_id

        except Exception as e:
            logger.error(f"Failed to send alert for {symbol}: {e}")
            return None

    def start(self):
        """Start the monitoring scheduler"""
        self.scheduler.add_job(
            self.scan_prices,
            'interval',
            seconds=SCAN_INTERVAL,
            id='price_scanner',
            replace_existing=True
        )
        self.scheduler.start()
        logger.info(f"✅ Price monitor started ({SCAN_INTERVAL}s interval, REST API)")

    def pause(self):
        """Pause scanning"""
        self.is_running = False
        logger.info("⏸️ Scanner paused")

    def resume(self):
        """Resume scanning"""
        self.is_running = True
        logger.info("▶️ Scanner resumed")

    def get_status(self):
        """Get scanner status"""
        return {
            'running': self.is_running,
            'scan_count': self.scan_count,
            'scan_interval': SCAN_INTERVAL
        }
