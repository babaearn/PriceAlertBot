"""
Alert Model
"""

from dataclasses import dataclass
from datetime import datetime, date
from typing import Optional


@dataclass
class Alert:
    """Alert history record"""
    id: int
    symbol: str
    threshold_percent: float
    alert_type: str  # 'gainer' or 'loser'
    trigger_price: float
    session_start_price: float
    actual_change_percent: float
    volume_24h: float
    telegram_message_id: Optional[int]
    session_date: date
    created_at: datetime

    def __repr__(self):
        return f"<Alert {self.symbol} {self.actual_change_percent:+.1f}%>"

    @property
    def is_gainer(self):
        """Check if alert is for gainer"""
        return self.alert_type == 'gainer'

    @property
    def is_loser(self):
        """Check if alert is for loser"""
        return self.alert_type == 'loser'

    @property
    def price_change(self):
        """Calculate absolute price change"""
        return self.trigger_price - self.session_start_price
