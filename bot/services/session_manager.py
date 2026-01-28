"""
Session Manager - Handle 00:00 UTC Daily Reset
"""

import logging
from datetime import datetime, date
from bot.services.database import cleanup_old_data, clear_session_prices

logger = logging.getLogger(__name__)


class SessionManager:
    """
    Manages daily session reset at 00:00 UTC
    - Clears old price snapshots
    - New day = new base price for % calculations
    - Alert history preserved per session_date
    """

    def __init__(self):
        self.last_reset_date = None

    def check_and_reset_session(self):
        """
        Check if we need to reset the session (new day)
        Called during each scan cycle
        """
        current_date = datetime.utcnow().date()

        # First run or new day detected
        if self.last_reset_date != current_date:
            logger.info(f"🔄 Session reset: {current_date}")

            # Cleanup old data (25+ hours old)
            try:
                cleanup_old_data()
                clear_session_prices()
            except Exception as e:
                logger.error(f"Cleanup failed: {e}")

            self.last_reset_date = current_date
            return True

        return False

    def is_new_session(self) -> bool:
        """Check if current session is new"""
        current_date = datetime.utcnow().date()
        return self.last_reset_date != current_date

    def get_session_date(self):
        """Get current session date"""
        return datetime.utcnow().date()


async def sync_session_prices():
    """
    Sync all session start prices to current prices.
    Called on startup to establish baseline for % calculations.

    This ensures:
    - All pairs have a session start price
    - Alerts can fire immediately after deployment
    - % changes are calculated from deployment time
    """
    from bot.services.price_fetcher import PriceFetcher
    from bot.services.database import save_session_start_price, get_connection

    logger.info("🔄 Syncing session prices to current market prices...")

    try:
        # Fetch all current prices from Bybit
        fetcher = PriceFetcher()
        all_tickers = fetcher.bybit.fetch_tickers()

        # Filter USDT pairs
        usdt_pairs = {
            symbol: ticker for symbol, ticker in all_tickers.items()
            if symbol.endswith('/USDT')
        }

        logger.info(f"📊 Found {len(usdt_pairs)} USDT pairs to sync")

        # Save session start prices
        synced = 0
        for symbol, ticker in usdt_pairs.items():
            try:
                price = float(ticker.get('last', 0) or 0)
                if price > 0:
                    save_session_start_price(symbol, price)
                    synced += 1
            except Exception as e:
                logger.debug(f"Error syncing {symbol}: {e}")

        logger.info(f"✅ Session sync complete: {synced} pairs synced")
        return synced

    except Exception as e:
        logger.error(f"❌ Session sync failed: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return 0


async def reset_session_full():
    """
    Full session reset - clears alert history and syncs prices.
    Called manually via /resetsession command.
    """
    from bot.services.database import get_connection
    from datetime import date

    logger.info("🔄 Full session reset initiated...")

    try:
        # Clear today's alert history
        conn = get_connection()
        try:
            today = date.today()
            with conn.cursor() as cur:
                cur.execute("""
                    DELETE FROM alert_history
                    WHERE session_date = %s
                """, (today,))
                deleted = cur.rowcount
                conn.commit()
                logger.info(f"🗑️ Cleared {deleted} alerts from today's history")
        finally:
            conn.close()

        # Clear session prices for today
        clear_session_prices()

        # Sync new prices
        synced = await sync_session_prices()

        logger.info(f"✅ Full session reset complete: {synced} pairs synced")
        return synced

    except Exception as e:
        logger.error(f"❌ Full session reset failed: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return 0
