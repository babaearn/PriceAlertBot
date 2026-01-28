"""
Price Monitoring Service - Native Bybit Scanner
Monitors ALL Bybit USDT pairs directly - NO database pair filtering
"""

import asyncio
import time
import logging
from datetime import datetime
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.events import EVENT_JOB_ERROR, EVENT_JOB_EXECUTED
from bot.services.price_fetcher import PriceFetcher
from bot.services.session_manager import SessionManager
from bot.services.database import log_scan_cycle
from bot.config import SCAN_INTERVAL, TELEGRAM_GROUP_ID, PRICE_ALERTS_TOPIC_ID, MIN_VOLUME_24H

logger = logging.getLogger(__name__)


class PriceMonitor:
    """
    Native Bybit price scanner
    Fetches ALL USDT pairs directly from Bybit API
    No database filtering - monitors everything
    """

    def __init__(self, bot_instance):
        self.bot = bot_instance
        self.fetcher = PriceFetcher()
        self.session_manager = SessionManager()

        # Configure scheduler with error handling
        job_defaults = {
            'coalesce': False,  # Run all missed executions
            'max_instances': 1,  # CRITICAL: Only ONE scan at a time to prevent race conditions
            'misfire_grace_time': 60  # Jobs can be 60s late
        }
        self.scheduler = AsyncIOScheduler(job_defaults=job_defaults)

        # Add error listener
        self.scheduler.add_listener(
            self._job_error_listener,
            EVENT_JOB_ERROR | EVENT_JOB_EXECUTED
        )

        self.scan_count = 0
        self.is_running = True

        # Statistics for logs.md
        self.last_scan_stats = {
            'pairs_checked': 0,
            'alerts_fired': 0,
            'errors': 0,
            'duration': 0,
            'last_scan_time': None
        }

    def _job_error_listener(self, event):
        """
        Listen for job errors and log them WITHOUT crashing the scheduler
        This prevents the hourly log writer from crashing the entire bot
        """
        if event.exception:
            logger.error(f"⚠️ Scheduler job error: {event.job_id}")
            logger.error(f"   Exception: {event.exception}")
            import traceback
            logger.error(f"   Traceback: {event.traceback}")
            logger.error("⚠️ Job failed but scheduler continues running")
        else:
            logger.debug(f"✅ Job executed successfully: {event.job_id}")

    async def scan_prices(self):
        """
        Main scan loop - fetches ALL Bybit pairs directly
        NO database queries for pairs - gets everything from Bybit API
        """
        if not self.is_running:
            logger.debug("Scanner paused")
            return

        start_time = time.time()
        self.scan_count += 1

        try:
            # Check for daily session reset (00:00 UTC) - NEVER crash the scanner
            try:
                if self.session_manager.check_and_reset_session():
                    logger.info("✅ Daily session reset complete")
            except Exception as reset_error:
                logger.error(f"⚠️ Session reset failed (non-fatal, continuing scan): {reset_error}")
                import traceback
                logger.error(traceback.format_exc())
                # Continue scanning even if reset fails

            logger.info(f"Scan #{self.scan_count}: Fetching ALL Bybit pairs...")

            # CRITICAL: Get ALL tickers directly from Bybit API
            all_tickers = self.fetcher.bybit.fetch_tickers()

            # Filter for USDT pairs only
            usdt_pairs = {
                symbol: ticker for symbol, ticker in all_tickers.items()
                if symbol.endswith('/USDT')
            }

            logger.info(f"Found {len(usdt_pairs)} USDT pairs on Bybit")

            total_checked = 0
            total_alerts = 0
            errors = 0

            # Import here to avoid circular imports
            from bot.services.alert_checker import check_and_fire_alerts_with_ai

            # Process each pair
            for symbol, ticker in usdt_pairs.items():
                try:
                    # Get price and volume from ticker (already fetched!)
                    price = float(ticker.get('last', 0) or 0)
                    volume_24h = float(ticker.get('quoteVolume', 0) or 0)

                    # Skip if no price
                    if price <= 0:
                        continue

                    # Skip low volume pairs
                    if volume_24h < MIN_VOLUME_24H:
                        continue

                    pair_data = {
                        'symbol': symbol,
                        'current_price': price,
                        'volume_24h': volume_24h
                    }

                    # Check thresholds - AI finds Adjust links when needed
                    alerts = await check_and_fire_alerts_with_ai(
                        pair_data,
                        self.send_alert
                    )

                    total_alerts += alerts
                    total_checked += 1

                except Exception as e:
                    logger.error(f"Error processing {symbol}: {e}")
                    errors += 1

            # Log scan results
            duration = time.time() - start_time
            log_scan_cycle(self.scan_count, total_checked, total_alerts, errors, duration)

            logger.info(
                f"Scan #{self.scan_count} complete: "
                f"{total_checked} pairs, {total_alerts} alerts, "
                f"{errors} errors, {duration:.2f}s"
            )

            # Update statistics for logs.md
            self.last_scan_stats = {
                'pairs_checked': total_checked,
                'alerts_fired': total_alerts,
                'errors': errors,
                'duration': duration,
                'last_scan_time': datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')
            }

        except Exception as e:
            logger.error(f"❌ CRITICAL: Scan error (recovering): {e}")
            import traceback
            logger.error(traceback.format_exc())

            # Update stats to show error
            self.last_scan_stats = {
                'pairs_checked': 0,
                'alerts_fired': 0,
                'errors': 1,
                'duration': time.time() - start_time,
                'last_scan_time': datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')
            }

            # CRITICAL: Do NOT crash - just log and continue to next scan
            logger.info("⚠️ Scan failed but scheduler will retry in next interval")

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

    def write_logs_hourly(self):
        """
        Write logs to logs.md file every hour for debugging
        IMPORTANT: This is SYNCHRONOUS to work with APScheduler
        """
        try:
            from bot.services.log_writer import write_logs_to_file_sync

            scan_stats = {
                'total_scans': self.scan_count,
                'scan_interval': SCAN_INTERVAL,
                'running': self.is_running,
                **self.last_scan_stats
            }

            write_logs_to_file_sync(scan_stats)
            logger.info("📝 Hourly logs written to logs.md")

        except Exception as e:
            logger.error(f"❌ CRITICAL: Hourly log write failed: {e}")
            import traceback
            logger.error(traceback.format_exc())
            # Don't crash - this is non-critical

    def start(self):
        """Start the monitoring scheduler"""
        # Install log capture on first start
        try:
            from bot.services.log_writer import install_log_capture
            install_log_capture()
        except Exception as e:
            logger.warning(f"Could not install log capture: {e}")

        # Schedule price scanning
        self.scheduler.add_job(
            self.scan_prices,
            'interval',
            seconds=SCAN_INTERVAL,
            id='price_scanner',
            replace_existing=True
        )

        # Schedule hourly log writing
        self.scheduler.add_job(
            self.write_logs_hourly,
            'interval',
            hours=1,
            id='log_writer',
            replace_existing=True
        )

        self.scheduler.start()
        logger.info(f"Price monitor started ({SCAN_INTERVAL}s interval) - Native Bybit Mode")
        logger.info("📝 Hourly log writer enabled (logs.md will update every hour)")

    def pause(self):
        """Pause scanning"""
        self.is_running = False
        logger.info("Scanner paused")

    def resume(self):
        """Resume scanning"""
        self.is_running = True
        logger.info("Scanner resumed")

    def update_interval(self, new_interval_seconds: int):
        """
        Dynamically update scan interval without restarting bot
        Reschedules the price scanner job with new interval
        """
        try:
            logger.info(f"🔄 Updating scan interval: {new_interval_seconds}s")

            # Reschedule the price scanner job with new interval
            self.scheduler.reschedule_job(
                job_id='price_scanner',
                trigger='interval',
                seconds=new_interval_seconds
            )

            logger.info(f"✅ Scan interval updated to {new_interval_seconds}s (live)")
            return True

        except Exception as e:
            logger.error(f"Failed to update scan interval: {e}")
            return False

    def get_status(self):
        """Get scanner status"""
        return {
            'running': self.is_running,
            'scan_count': self.scan_count,
            'scan_interval': SCAN_INTERVAL
        }
