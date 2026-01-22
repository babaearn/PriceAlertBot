"""
Price Fetching Service - REST API with CCXT
Primary: Bybit | Fallback: Binance
"""

import ccxt
from typing import List, Dict
import logging
from tenacity import retry, stop_after_attempt, wait_fixed

logger = logging.getLogger(__name__)


class PriceFetcher:
    """
    Fetch prices via REST API using CCXT
    Primary: Bybit | Fallback: Binance
    """

    def __init__(self):
        self.bybit = ccxt.bybit({
            'enableRateLimit': True,
            'timeout': 10000,
            'options': {'defaultType': 'spot'}
        })

        self.binance = ccxt.binance({
            'enableRateLimit': True,
            'timeout': 10000,
            'options': {'defaultType': 'spot'}
        })

    @retry(stop=stop_after_attempt(3), wait=wait_fixed(2))
    def fetch_batch_prices_bybit(self, symbols: List[str]) -> Dict[str, dict]:
        """Fetch prices from Bybit"""
        try:
            tickers = self.bybit.fetch_tickers(symbols)
            results = {}

            for symbol, ticker in tickers.items():
                if ticker['last'] and ticker['quoteVolume']:
                    results[symbol] = {
                        'price': float(ticker['last']),
                        'volume_24h': float(ticker['quoteVolume']),
                        'source': 'bybit'
                    }

            logger.debug(f"Bybit: Fetched {len(results)}/{len(symbols)} prices")
            return results

        except Exception as e:
            logger.error(f"Bybit fetch failed: {e}")
            raise

    @retry(stop=stop_after_attempt(3), wait=wait_fixed(2))
    def fetch_batch_prices_binance(self, symbols: List[str]) -> Dict[str, dict]:
        """Fetch prices from Binance (fallback)"""
        try:
            tickers = self.binance.fetch_tickers(symbols)
            results = {}

            for symbol, ticker in tickers.items():
                if ticker['last'] and ticker['quoteVolume']:
                    results[symbol] = {
                        'price': float(ticker['last']),
                        'volume_24h': float(ticker['quoteVolume']),
                        'source': 'binance'
                    }

            logger.debug(f"Binance: Fetched {len(results)}/{len(symbols)} prices")
            return results

        except Exception as e:
            logger.error(f"Binance fetch failed: {e}")
            raise

    def fetch_batch_prices(self, symbols: List[str]) -> Dict[str, dict]:
        """
        Fetch prices with automatic fallback
        Primary: Bybit → Fallback: Binance
        """
        # Try Bybit first
        try:
            return self.fetch_batch_prices_bybit(symbols)
        except Exception as e:
            logger.warning(f"Bybit failed: {e}, trying Binance...")

        # Fallback to Binance
        try:
            return self.fetch_batch_prices_binance(symbols)
        except Exception as e:
            logger.error(f"Both APIs failed for batch: {e}")
            return {}

    def fetch_single_price(self, symbol: str) -> Dict[str, any]:
        """
        Fetch single symbol price (for testing/admin commands)
        """
        return self.fetch_batch_prices([symbol]).get(symbol, {})
