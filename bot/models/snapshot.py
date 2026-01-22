"""
Price Snapshot Model
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class PriceSnapshot:
    """Price snapshot at a point in time"""
    id: int
    symbol: str
    price: float
    volume_24h: float
    session_start_price: Optional[float]
    timestamp: datetime
    source: str  # 'bybit' or 'binance'

    def __repr__(self):
        return f"<PriceSnapshot {self.symbol} ${self.price} @ {self.timestamp}>"

    @property
    def change_from_session_start(self):
        """Calculate % change from session start"""
        if not self.session_start_price or self.session_start_price == 0:
            return 0.0

        return ((self.price - self.session_start_price) / self.session_start_price) * 100

    @property
    def price_change(self):
        """Calculate absolute price change from session start"""
        if not self.session_start_price:
            return 0.0

        return self.price - self.session_start_price
