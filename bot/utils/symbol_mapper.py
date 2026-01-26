"""
Symbol Mapper - Maps Mudrex symbols to exchange-specific symbols
Handles:
- Multiplier prefixes (SHIB1000 → 1000SHIB)
- Rebranded tokens (MATIC → POL)
- Merged tokens (AGIX → FET)
"""

import logging
from typing import Optional, Dict

logger = logging.getLogger(__name__)

# Manual symbol mappings for known differences
# Format: "mudrex_symbol": "exchange_symbol" or None if unavailable
SYMBOL_MAPPINGS: Dict[str, Optional[str]] = {
    # Multiplier prefix fixes (Mudrex → Bybit)
    "SHIB1000/USDT": "1000SHIB/USDT",
    "1000SHIB/USDT": "1000SHIB/USDT",
    "1000SHIBUSDT/USDT": "1000SHIB/USDT",

    # Rebranded tokens
    "MATIC/USDT": "POL/USDT",  # Polygon rebrand

    # Merged tokens
    "AGIX/USDT": "FET/USDT",   # Merged into Fetch.ai
    "OCEAN/USDT": "FET/USDT",  # Merged into Fetch.ai

    # Special format tokens
    "1000WHY/USDT": "1000WHY/USDT",
    "1000PEPE/USDT": "1000PEPE/USDT",
    "1000BONK/USDT": "1000BONK/USDT",
    "1000FLOKI/USDT": "1000FLOKI/USDT",
    "1000NEIROCTO/USDT": "1000NEIROCTO/USDT",
    "1000RATS/USDT": "1000RATS/USDT",
    "1000TURBO/USDT": "1000TURBO/USDT",
    "1000CAT/USDT": "1000CAT/USDT",
    "1000LUNC/USDT": "1000LUNC/USDT",
    "1000BTT/USDT": "1000BTT/USDT",
    "1000XEC/USDT": "1000XEC/USDT",
    "1000TAG/USDT": "1000TAG/USDT",
    "10000SATS/USDT": "10000SATS/USDT",
    "10000ELON/USDT": "10000ELON/USDT",
    "10000QUBIC/USDT": "10000QUBIC/USDT",
    "1000000BABYDOGE/USDT": "1000000BABYDOGE/USDT",
    "1000000CHEEMS/USDT": "1000000CHEEMS/USDT",

    # Tokens that may not exist on Bybit (mark as None to skip)
    # These will be auto-detected by Gemini or can be manually set
}

# Tokens known to be unavailable on Bybit
UNAVAILABLE_SYMBOLS = {
    # Add symbols that don't exist on any exchange
    # These will be skipped during price fetching
}


def map_symbol_to_exchange(mudrex_symbol: str, exchange: str = 'bybit') -> Optional[str]:
    """
    Map a Mudrex symbol to the corresponding exchange symbol

    Args:
        mudrex_symbol: Symbol from Mudrex database (e.g., "SHIB1000/USDT")
        exchange: Target exchange ('bybit' or 'binance')

    Returns:
        Exchange-specific symbol or None if unavailable
    """
    # Check if unavailable
    if mudrex_symbol in UNAVAILABLE_SYMBOLS:
        return None

    # Check manual mappings
    if mudrex_symbol in SYMBOL_MAPPINGS:
        return SYMBOL_MAPPINGS[mudrex_symbol]

    # Auto-detect multiplier prefix patterns
    # Pattern: TOKEN1000/USDT → 1000TOKEN/USDT
    base = mudrex_symbol.replace('/USDT', '')

    # Check for suffix multipliers (SHIB1000 → 1000SHIB)
    for multiplier in ['1000000', '10000', '1000']:
        if base.endswith(multiplier):
            token = base[:-len(multiplier)]
            mapped = f"{multiplier}{token}/USDT"
            logger.debug(f"Auto-mapped: {mudrex_symbol} → {mapped}")
            return mapped

    # No mapping needed, return as-is
    return mudrex_symbol


def is_symbol_available(symbol: str) -> bool:
    """
    Check if a symbol is available for price fetching

    Args:
        symbol: Symbol to check

    Returns:
        True if available, False if known to be unavailable
    """
    if symbol in UNAVAILABLE_SYMBOLS:
        return False

    if symbol in SYMBOL_MAPPINGS and SYMBOL_MAPPINGS[symbol] is None:
        return False

    return True


def add_mapping(mudrex_symbol: str, exchange_symbol: Optional[str]):
    """
    Add or update a symbol mapping

    Args:
        mudrex_symbol: Symbol from Mudrex
        exchange_symbol: Exchange symbol or None if unavailable
    """
    SYMBOL_MAPPINGS[mudrex_symbol] = exchange_symbol
    if exchange_symbol:
        logger.info(f"Added mapping: {mudrex_symbol} → {exchange_symbol}")
    else:
        UNAVAILABLE_SYMBOLS.add(mudrex_symbol)
        logger.info(f"Marked unavailable: {mudrex_symbol}")


def get_all_mappings() -> Dict[str, Optional[str]]:
    """Get all current symbol mappings"""
    return SYMBOL_MAPPINGS.copy()


def get_unavailable_symbols() -> set:
    """Get set of unavailable symbols"""
    return UNAVAILABLE_SYMBOLS.copy()
