"""
Price Fetching Service - REST API with CCXT
Primary: Bybit | Fallback: Binance
Supports: Symbol mapping, API toggle
"""

import ccxt
from typing import List, Dict
import logging
from tenacity import retry, stop_after_attempt, wait_fixed
from bot.utils.symbol_mapper import map_symbol_to_exchange, is_symbol_available
from bot.services.database import get_config_value

logger = logging.getLogger(__name__)


class PriceFetcher:
    """
    Fetch prices via REST API using CCXT
    Primary: Bybit | Fallback: Binance
    Supports symbol mapping and API toggle
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

    def is_bybit_enabled(self) -> bool:
        """Check if Bybit API is enabled"""
        return get_config_value('api_bybit_enabled', 'true') == 'true'

    def is_binance_enabled(self) -> bool:
        """Check if Binance API is enabled"""
        return get_config_value('api_binance_enabled', 'true') == 'true'

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
        Fetch prices with symbol mapping and API toggle support
        Primary: Bybit → Fallback: Binance
        """
        # Map symbols and filter unavailable ones
        mapped_symbols = {}  # exchange_symbol -> original_symbol
        available_symbols = []

        for symbol in symbols:
            if not is_symbol_available(symbol):
                logger.debug(f"Skipping unavailable: {symbol}")
                continue

            exchange_symbol = map_symbol_to_exchange(symbol, 'bybit')
            if exchange_symbol:
                mapped_symbols[exchange_symbol] = symbol
                available_symbols.append(exchange_symbol)

        if not available_symbols:
            logger.warning("No available symbols to fetch")
            return {}

        final_results = {}

        # Try Bybit if enabled
        if self.is_bybit_enabled():
            try:
                results = self.fetch_batch_prices_bybit(available_symbols)
                for ex_sym, data in results.items():
                    orig_sym = mapped_symbols.get(ex_sym, ex_sym)
                    final_results[orig_sym] = data

                logger.debug(f"🔵 Bybit: {len(final_results)}/{len(symbols)} prices")

                if final_results:
                    return final_results

            except Exception as e:
                logger.warning(f"🔵 Bybit failed: {e}")

                if not self.is_binance_enabled():
                    logger.error("⚠️ Binance disabled, no fallback available")
                    return final_results
        else:
            logger.debug("🔵 Bybit disabled, skipping...")

        # Try Binance if enabled
        if self.is_binance_enabled():
            try:
                results = self.fetch_batch_prices_binance(available_symbols)
                for ex_sym, data in results.items():
                    orig_sym = mapped_symbols.get(ex_sym, ex_sym)
                    if orig_sym not in final_results:
                        final_results[orig_sym] = data

                logger.debug(f"🟡 Binance: {len(final_results)}/{len(symbols)} prices")
                return final_results

            except Exception as e:
                logger.error(f"🟡 Binance failed: {e}")
                return final_results
        else:
            logger.debug("🟡 Binance disabled, skipping...")

        return final_results

    def fetch_single_price(self, symbol: str) -> Dict[str, any]:
        """
        Fetch single symbol price (for testing/admin commands)
        """
        return self.fetch_batch_prices([symbol]).get(symbol, {})
