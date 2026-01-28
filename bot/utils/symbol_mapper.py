"""
Symbol mapping with dual mode: Manual (predefined) or AI (Gemini)
Toggle with /ai command
"""

import logging
import json
from typing import Optional, Dict

logger = logging.getLogger(__name__)

# ==========================================
# MODE 1: MANUAL PREDEFINED MAPPINGS
# ==========================================

MANUAL_SYMBOL_MAP: Dict[str, Optional[str]] = {
    # Multiplier prefixes (1000x, 10000x)
    "SHIB1000/USDT": "1000SHIB/USDT",
    "1000SHIBUSDT/USDT": "1000SHIB/USDT",
    "10000SATS/USDT": "10000SATS/USDT",
    "1000BONK/USDT": "1000BONK/USDT",
    "1000FLOKI/USDT": "1000FLOKI/USDT",
    "1000PEPE/USDT": "1000PEPE/USDT",
    "1000RATS/USDT": "1000RATS/USDT",
    "1000BTT/USDT": "1000BTT/USDT",
    "1000CAT/USDT": "1000CAT/USDT",
    "1000LUNC/USDT": "1000LUNC/USDT",
    "1000TURBO/USDT": "1000TURBO/USDT",
    "1000XEC/USDT": "1000XEC/USDT",
    "1000WHY/USDT": "1000WHY/USDT",
    "1000TAG/USDT": "TAG/USDT",
    "1000NEIROCTO/USDT": "NEIRO/USDT",
    "1000000BABYDOGE/USDT": "1000000BABYDOGE/USDT",
    "1000000CHEEMS/USDT": "CHEEMS/USDT",
    "10000ELON/USDT": "10000ELON/USDT",
    "10000QUBIC/USDT": "10000QUBIC/USDT",

    # Rebranded tokens
    "MATIC/USDT": "POL/USDT",  # Polygon rebrand

    # Merged tokens
    "AGIX/USDT": "FET/USDT",   # Merged into Fetch.ai
    "OCEAN/USDT": "FET/USDT",  # Merged into Fetch.ai

    # Different naming
    "RAYDIUM/USDT": "RAY/USDT",
    "DIA1/USDT": "DIA/USDT",
    "AGLD1/USDT": "AGLD/USDT",
    "TRB1/USDT": "TRB/USDT",
    "ZRX1/USDT": "ZRX/USDT",
    "AVAX1/USDT": "AVAX/USDT",
    "RUNE1/USDT": "RUNE/USDT",

    # Unavailable pairs (skip these)
    "STG/USDT": None,
    "SUKU/USDT": None,
    "XCH/USDT": None,
    "WEMIX/USDT": None,
    "ARPA/USDT": None,
    "ASP/USDT": None,
    "CHESS/USDT": None,
    "ETHBTC/USDT": None,
    "IOST/USDT": None,
    "MTL/USDT": None,
    "QI/USDT": None,
}

# ==========================================
# MODE 2: AI-POWERED MAPPINGS (GEMINI)
# ==========================================

# Cache for AI-generated mappings
AI_SYMBOL_CACHE: Dict[str, Optional[str]] = {}
AI_CACHE_FILE = '/tmp/gemini_symbol_mappings.json'


def load_ai_cache():
    """Load AI-generated mappings from file"""
    global AI_SYMBOL_CACHE
    try:
        with open(AI_CACHE_FILE, 'r') as f:
            AI_SYMBOL_CACHE = json.load(f)
        logger.info(f"📂 Loaded {len(AI_SYMBOL_CACHE)} AI mappings from cache")
        return True
    except FileNotFoundError:
        logger.info("No AI cache found, will use manual mappings")
        return False
    except Exception as e:
        logger.warning(f"Failed to load AI cache: {e}")
        return False


def save_ai_cache(mappings: Dict[str, Optional[str]]):
    """Save AI-generated mappings to file"""
    global AI_SYMBOL_CACHE
    try:
        with open(AI_CACHE_FILE, 'w') as f:
            json.dump(mappings, f, indent=2)
        AI_SYMBOL_CACHE = mappings
        logger.info(f"💾 Saved {len(mappings)} AI mappings to cache")
        return True
    except Exception as e:
        logger.error(f"Failed to save AI cache: {e}")
        return False


def get_ai_cache_stats() -> Dict:
    """Get statistics about AI cache"""
    if not AI_SYMBOL_CACHE:
        load_ai_cache()

    if not AI_SYMBOL_CACHE:
        return {"loaded": False, "count": 0}

    available = sum(1 for v in AI_SYMBOL_CACHE.values() if v is not None)
    unavailable = sum(1 for v in AI_SYMBOL_CACHE.values() if v is None)
    mapped = sum(1 for k, v in AI_SYMBOL_CACHE.items() if v and k != v)

    return {
        "loaded": True,
        "count": len(AI_SYMBOL_CACHE),
        "available": available,
        "unavailable": unavailable,
        "mapped": mapped
    }


# Load cache on import
load_ai_cache()


# ==========================================
# CONFIGURATION: AI MODE TOGGLE
# ==========================================

def get_ai_mode_status() -> bool:
    """Check if AI mode is enabled"""
    from bot.services.database import get_config_value
    return get_config_value('ai_mode_enabled', 'false') == 'true'


def map_symbol_to_exchange(mudrex_symbol: str, exchange: str = 'bybit') -> Optional[str]:
    """
    Map Mudrex symbol to exchange symbol
    Uses AI cache if enabled, otherwise uses manual mappings
    """
    ai_mode = get_ai_mode_status()

    if ai_mode and AI_SYMBOL_CACHE:
        # AI MODE: Use Gemini cache
        if mudrex_symbol in AI_SYMBOL_CACHE:
            mapped = AI_SYMBOL_CACHE[mudrex_symbol]
            if mapped is None:
                logger.debug(f"🧠 AI: {mudrex_symbol} unavailable on {exchange}")
                return None
            if mapped != mudrex_symbol:
                logger.debug(f"🧠 AI mapped: {mudrex_symbol} → {mapped}")
            return mapped
    else:
        # MANUAL MODE: Use predefined mappings
        if mudrex_symbol in MANUAL_SYMBOL_MAP:
            mapped = MANUAL_SYMBOL_MAP[mudrex_symbol]
            if mapped is None:
                logger.debug(f"📖 Manual: {mudrex_symbol} unavailable")
                return None
            if mapped != mudrex_symbol:
                logger.debug(f"📖 Manual mapped: {mudrex_symbol} → {mapped}")
            return mapped

    # Auto-detect multiplier prefix patterns
    # Pattern: TOKEN1000/USDT → 1000TOKEN/USDT
    base = mudrex_symbol.replace('/USDT', '')

    for multiplier in ['1000000', '10000', '1000']:
        if base.endswith(multiplier):
            token = base[:-len(multiplier)]
            mapped = f"{multiplier}{token}/USDT"
            logger.debug(f"Auto-mapped: {mudrex_symbol} → {mapped}")
            return mapped

    # Default: assume symbol is correct
    return mudrex_symbol


def is_symbol_available(mudrex_symbol: str) -> bool:
    """Check if symbol is available"""
    ai_mode = get_ai_mode_status()

    if ai_mode and AI_SYMBOL_CACHE:
        if mudrex_symbol in AI_SYMBOL_CACHE:
            return AI_SYMBOL_CACHE[mudrex_symbol] is not None
    else:
        if mudrex_symbol in MANUAL_SYMBOL_MAP:
            return MANUAL_SYMBOL_MAP[mudrex_symbol] is not None

    return True  # Assume available if not in mappings


def add_mapping(mudrex_symbol: str, exchange_symbol: Optional[str]):
    """
    Add or update a symbol mapping (to manual map)
    """
    MANUAL_SYMBOL_MAP[mudrex_symbol] = exchange_symbol
    if exchange_symbol:
        logger.info(f"Added mapping: {mudrex_symbol} → {exchange_symbol}")
    else:
        logger.info(f"Marked unavailable: {mudrex_symbol}")


def get_all_mappings() -> Dict[str, Optional[str]]:
    """Get all current symbol mappings (based on current mode)"""
    if get_ai_mode_status() and AI_SYMBOL_CACHE:
        return AI_SYMBOL_CACHE.copy()
    return MANUAL_SYMBOL_MAP.copy()
