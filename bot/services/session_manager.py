"""
Session Manager - Handle 00:00 UTC Daily Reset
"""

import logging
from datetime import datetime, time
from bot.services.database import cleanup_old_data

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
