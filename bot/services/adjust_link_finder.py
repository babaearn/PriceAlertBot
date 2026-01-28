"""
AI-powered Adjust link finder using Gemini 2.5 Flash
Finds Mudrex Adjust links for Bybit symbols on-demand
"""

import json
import os
import logging
from typing import Optional, Dict

logger = logging.getLogger(__name__)

# Gemini configuration
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')

# Lazy-loaded Gemini model
_model = None

# In-memory cache (faster than DB for repeated lookups)
_memory_cache: Dict[str, Optional[str]] = {}


def _get_model():
    """Get or initialize Gemini model"""
    global _model

    if _model is not None:
        return _model

    if not GEMINI_API_KEY:
        logger.warning("GEMINI_API_KEY not set")
        return None

    try:
        import google.generativeai as genai
        genai.configure(api_key=GEMINI_API_KEY)
        _model = genai.GenerativeModel(
            'gemini-2.5-flash',
            generation_config={'temperature': 0.1}
        )
        logger.info("Gemini model initialized")
        return _model
    except Exception as e:
        logger.error(f"Failed to init Gemini: {e}")
        return None


async def find_adjust_link_with_ai(bybit_symbol: str) -> Optional[str]:
    """
    Find Mudrex Adjust link for a Bybit symbol
    1. Check memory cache (instant)
    2. Check JSON file cache (fast)
    3. Check database cache (fast)
    4. Use Gemini AI (slow, but cached)
    """
    # 1. Memory cache (instant)
    if bybit_symbol in _memory_cache:
        cached = _memory_cache[bybit_symbol]
        if cached == '':
            return None  # Marked as unavailable
        return cached

    # 2. JSON file cache (from data/adjust_links.json)
    from bot.services.adjust_links import find_adjust_link

    json_cached = find_adjust_link(bybit_symbol)
    if json_cached:
        _memory_cache[bybit_symbol] = json_cached
        logger.info(f"✅ {bybit_symbol}: Found link in JSON cache -> {json_cached}")
        return json_cached

    # 3. Database cache (checks both adjust_link_cache AND active_pairs tables)
    from bot.services.database import get_cached_adjust_link, cache_adjust_link

    db_cached = get_cached_adjust_link(bybit_symbol)
    if db_cached is not None:
        _memory_cache[bybit_symbol] = db_cached
        if db_cached == '':
            logger.debug(f"🚫 {bybit_symbol}: Marked as unavailable in DB")
            return None
        logger.debug(f"✅ {bybit_symbol}: Found link in DB")
        return db_cached

    # 4. AI lookup (only if not cached)
    model = _get_model()
    if not model:
        return None

    logger.info(f"AI: Looking up {bybit_symbol}...")

    # Load known links for context
    from bot.services.database import get_all_known_adjust_links
    known_links = get_all_known_adjust_links()
    sample_links = dict(list(known_links.items())[:30])

    prompt = f"""Find the Mudrex Adjust deeplink for Bybit symbol: {bybit_symbol}

Known Mudrex links (sample):
{json.dumps(sample_links, indent=2)}

Rules:
- Bybit: "1000SHIB/USDT" → Mudrex might be "SHIB1000/USDT" or similar
- Match patterns: multiplier swaps, exact matches
- Return JSON only (no markdown):

If found:
{{"found": true, "adjust_link": "https://mudrex.go.link/xxxxx"}}

If not found:
{{"found": false, "adjust_link": null}}"""

    try:
        response = model.generate_content(prompt)
        text = response.text.strip()

        # Clean markdown
        if '```' in text:
            text = text.split('```')[1]
            if text.startswith('json'):
                text = text[4:]
            text = text.strip()

        result = json.loads(text)
        link = result.get('adjust_link')

        if link:
            # Cache success
            cache_adjust_link(bybit_symbol, link, 'ai')
            _memory_cache[bybit_symbol] = link
            logger.info(f"AI found: {bybit_symbol} -> {link[:40]}...")
            return link
        else:
            # Cache as unavailable
            cache_adjust_link(bybit_symbol, '', 'ai')
            _memory_cache[bybit_symbol] = ''
            logger.info(f"AI: No link for {bybit_symbol}")
            return None

    except Exception as e:
        logger.error(f"AI error for {bybit_symbol}: {e}")
        # Don't cache errors - might work next time
        return None


def clear_memory_cache():
    """Clear in-memory cache (for testing)"""
    global _memory_cache
    _memory_cache = {}
