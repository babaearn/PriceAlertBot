"""
Gemini AI Symbol Resolver
Uses Google's Gemini AI to automatically map Mudrex symbols to exchange symbols
"""

import os
import logging
import time
from typing import Optional, Dict, List

logger = logging.getLogger(__name__)

# Gemini API configuration
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
GEMINI_MODEL = 'gemini-1.5-flash'

# Initialize Gemini client
genai = None
model = None


def init_gemini():
    """Initialize Gemini API client"""
    global genai, model

    if not GEMINI_API_KEY:
        logger.warning("⚠️ GEMINI_API_KEY not set, AI resolution disabled")
        return False

    try:
        import google.generativeai as genai_module
        genai_module.configure(api_key=GEMINI_API_KEY)
        genai = genai_module
        model = genai.GenerativeModel(GEMINI_MODEL)
        logger.info("✅ Gemini AI initialized")
        return True
    except ImportError:
        logger.warning("⚠️ google-generativeai not installed, AI resolution disabled")
        return False
    except Exception as e:
        logger.error(f"❌ Failed to initialize Gemini: {e}")
        return False


def resolve_symbol_with_gemini(mudrex_symbol: str, bybit_symbols: List[str]) -> Optional[str]:
    """
    Use Gemini AI to find the correct Bybit symbol for a Mudrex symbol

    Args:
        mudrex_symbol: Symbol from Mudrex (e.g., "SHIB1000/USDT")
        bybit_symbols: List of available symbols on Bybit

    Returns:
        Matched Bybit symbol or None if unavailable
    """
    global model

    if model is None:
        if not init_gemini():
            return None

    prompt = f"""You are a cryptocurrency symbol mapping expert. Your task is to find the correct Bybit symbol that matches a Mudrex symbol.

**Mudrex Symbol:** {mudrex_symbol}

**Available Bybit Symbols (sample):**
{', '.join(bybit_symbols[:150])}

**Common Patterns:**
1. Multiplier prefixes: "SHIB1000/USDT" on Mudrex = "1000SHIB/USDT" on Bybit
2. Number prefixes: "1000PEPE/USDT" stays same on both
3. Rebranded: "MATIC/USDT" = "POL/USDT" (Polygon rebrand)
4. Merged: "AGIX/USDT" = "FET/USDT" (merged into Fetch.ai)
5. Some tokens simply don't exist on Bybit

**Instructions:**
- If the symbol exists on Bybit with the same name, return it
- If it has a multiplier suffix, adjust the format (SHIB1000 → 1000SHIB)
- If the token was rebranded/merged, return the new symbol
- If no match exists on Bybit, return "UNAVAILABLE"

**Output Format:**
Return ONLY the Bybit symbol or "UNAVAILABLE", nothing else.

Now resolve: {mudrex_symbol}"""

    try:
        response = model.generate_content(prompt)
        result = response.text.strip()

        # Clean up response
        result = result.replace('`', '').strip()

        if result == "UNAVAILABLE":
            logger.info(f"🧠 Gemini: {mudrex_symbol} not available on Bybit")
            return None

        # Check if result looks like a valid symbol
        if '/USDT' in result:
            logger.info(f"🧠 Gemini mapped: {mudrex_symbol} → {result}")
            return result

        logger.warning(f"🧠 Gemini returned invalid format: {result}")
        return None

    except Exception as e:
        logger.error(f"🧠 Gemini API error: {e}")
        return None


def auto_generate_mappings(mudrex_symbols: List[str], bybit_symbols: List[str],
                           progress_callback=None) -> Dict[str, Optional[str]]:
    """
    Use Gemini to auto-generate symbol mappings for all pairs

    Args:
        mudrex_symbols: List of symbols from Mudrex
        bybit_symbols: List of available symbols on Bybit
        progress_callback: Optional async function to report progress

    Returns:
        Dictionary of {mudrex_symbol: bybit_symbol or None}
    """
    mappings = {}

    logger.info(f"🧠 Starting Gemini auto-mapping for {len(mudrex_symbols)} symbols...")

    for i, symbol in enumerate(mudrex_symbols, 1):
        # Skip if already matches
        if symbol in bybit_symbols:
            mappings[symbol] = symbol
            logger.debug(f"✅ {i}/{len(mudrex_symbols)}: {symbol} exists on Bybit")
            continue

        # Use Gemini to resolve
        bybit_symbol = resolve_symbol_with_gemini(symbol, bybit_symbols)
        mappings[symbol] = bybit_symbol

        if bybit_symbol:
            logger.info(f"🧠 {i}/{len(mudrex_symbols)}: {symbol} → {bybit_symbol}")
        else:
            logger.info(f"🧠 {i}/{len(mudrex_symbols)}: {symbol} → UNAVAILABLE")

        # Rate limiting: Wait 1 second between API calls
        if i < len(mudrex_symbols):
            time.sleep(1)

    # Summary
    available = sum(1 for v in mappings.values() if v is not None)
    unavailable = sum(1 for v in mappings.values() if v is None)

    logger.info(f"🧠 Gemini mapping complete: {available} available, {unavailable} unavailable")

    return mappings


def is_gemini_available() -> bool:
    """Check if Gemini API is available"""
    return GEMINI_API_KEY is not None and GEMINI_API_KEY != ''
