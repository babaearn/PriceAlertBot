"""
Active Pair Model
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class ActivePair:
    """Trading pair with Adjust link"""
    id: int
    symbol: str
    adjust_link: str
    status: str = 'active'
    added_by: Optional[str] = None
    added_at: Optional[datetime] = None
    last_scanned: Optional[datetime] = None

    def __repr__(self):
        return f"<ActivePair {self.symbol}>"

    @property
    def clean_symbol(self):
        """Get symbol without /USDT"""
        return self.symbol.replace('/USDT', '')

    @property
    def is_active(self):
        """Check if pair is active"""
        return self.status == 'active'
