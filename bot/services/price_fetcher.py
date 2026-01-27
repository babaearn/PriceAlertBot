"""
Price Fetching Service - Bybit REST API via CCXT
Simple wrapper for Bybit API - scanner uses fetch_tickers() directly
"""

import ccxt
import logging

logger = logging.getLogger(__name__)


class PriceFetcher:
    """
    Simple Bybit API wrapper using CCXT
    Scanner uses self.bybit.fetch_tickers() directly for ALL pairs
    """

    def __init__(self):
        # Bybit - Primary exchange
        self.bybit = ccxt.bybit({
            'enableRateLimit': True,
            'timeout': 15000,  # 15 second timeout
            'options': {'defaultType': 'spot'}
        })

        # Binance - Available for fallback if needed
        self.binance = ccxt.binance({
            'enableRateLimit': True,
            'timeout': 15000,
            'options': {'defaultType': 'spot'}
        })

        logger.info("PriceFetcher initialized (Bybit + Binance)")

    def test_connection(self) -> dict:
        """Test API connections - used by /test command"""
        results = {
            'bybit': {'status': 'unknown', 'price': None},
            'binance': {'status': 'unknown', 'price': None}
        }

        # Test Bybit
        try:
            ticker = self.bybit.fetch_ticker('BTC/USDT')
            if ticker and ticker.get('last'):
                results['bybit'] = {
                    'status': 'online',
                    'price': float(ticker['last'])
                }
        except Exception as e:
            results['bybit'] = {'status': 'error', 'error': str(e)}

        # Test Binance
        try:
            ticker = self.binance.fetch_ticker('BTC/USDT')
            if ticker and ticker.get('last'):
                results['binance'] = {
                    'status': 'online',
                    'price': float(ticker['last'])
                }
        except Exception as e:
            results['binance'] = {'status': 'error', 'error': str(e)}

        return results
