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
GEMINI_MODEL = 'gemini-2.5-flash'

# Lazy-loaded Gemini client
genai = None
model = None

# Known Adjust links database (loaded for AI context)
KNOWN_LINKS_DATABASE: Dict[str, str] = {}


def init_gemini():
    """Initialize Gemini API client"""
    global genai, model

    if not GEMINI_API_KEY:
        logger.warning("GEMINI_API_KEY not set, AI link finder disabled")
        return False

    try:
        import google.generativeai as genai_module
        genai_module.configure(api_key=GEMINI_API_KEY)
        genai = genai_module
        model = genai.GenerativeModel(
            GEMINI_MODEL,
            generation_config={
                'temperature': 0.1,  # Low temp for consistent results
            }
        )
        logger.info("Gemini AI initialized for Adjust link finder")
        return True
    except ImportError:
        logger.warning("google-generativeai not installed, AI link finder disabled")
        return False
    except Exception as e:
        logger.error(f"Failed to initialize Gemini: {e}")
        return False


def is_gemini_available() -> bool:
    """Check if Gemini API is available"""
    return GEMINI_API_KEY is not None and GEMINI_API_KEY != ''


def load_known_links_database():
    """Load known Adjust links from database for AI context"""
    global KNOWN_LINKS_DATABASE

    try:
        from bot.services.database import get_all_known_adjust_links
        KNOWN_LINKS_DATABASE = get_all_known_adjust_links()
        logger.info(f"Loaded {len(KNOWN_LINKS_DATABASE)} known Adjust links for AI context")
    except Exception as e:
        logger.warning(f"Failed to load known links: {e}")


async def find_adjust_link_with_ai(bybit_symbol: str) -> Optional[str]:
    """
    Find Mudrex Adjust link for a Bybit symbol using AI

    Process:
    1. Check cache first (instant)
    2. If not cached, use Gemini AI to find link
    3. Cache result for future use

    Args:
        bybit_symbol: Bybit symbol (e.g., "1000SHIB/USDT", "BTC/USDT")

    Returns:
        Adjust link URL or None if not found
    """
    global model

    from bot.services.database import get_cached_adjust_link, cache_adjust_link

    # 1. Check cache first
    cached = get_cached_adjust_link(bybit_symbol)

    if cached is not None:
        if cached == '':
            # Explicitly marked as unavailable
            logger.debug(f"Cache: {bybit_symbol} not available on Mudrex")
            return None
        else:
            logger.debug(f"Cache hit: {bybit_symbol}")
            return cached

    # 2. Check if AI is available
    if not is_gemini_available():
        logger.debug(f"Gemini not available, skipping AI lookup for {bybit_symbol}")
        return None

    # 3. Initialize Gemini if needed
    if model is None:
        if not init_gemini():
            return None

    # 4. Load known links if empty
    if not KNOWN_LINKS_DATABASE:
        load_known_links_database()

    logger.info(f"AI: Finding Adjust link for {bybit_symbol}...")

    # Prepare known links sample for AI context
    sample_links = dict(list(KNOWN_LINKS_DATABASE.items())[:50])

    prompt = f"""You are an expert at matching cryptocurrency symbols between Bybit and Mudrex exchanges.

**Task:** Find the Mudrex Adjust deeplink for this Bybit trading pair.

**Bybit Symbol:** {bybit_symbol}

**Known Mudrex Adjust Links (reference sample):**
{json.dumps(sample_links, indent=2)}

**Pattern Recognition Rules:**
1. Bybit uses: "1000SHIB/USDT", "BTC/USDT", "ETH/USDT"
2. Mudrex might use same or variations: "SHIB1000/USDT", "1000SHIBUSDT/USDT"
3. Try exact match first
4. Then try common variations:
   - Remove multiplier prefix (1000, 10000)
   - Swap multiplier position
   - Remove /USDT suffix for matching

**Instructions:**
1. Search known links for exact or close matches
2. If found, return the Adjust link
3. If not found, return null

**Output Format (JSON only, no markdown):**
{{
  "found": true,
  "mudrex_symbol": "SHIB1000",
  "adjust_link": "https://mudrex.go.link/xxxxx"
}}

OR if not found:
{{
  "found": false,
  "adjust_link": null
}}

Find link for {bybit_symbol}:"""

    try:
        response = model.generate_content(prompt)
        result_text = response.text.strip()

        # Clean markdown if present
        if '```' in result_text:
            parts = result_text.split('```')
            if len(parts) >= 2:
                result_text = parts[1]
                if result_text.startswith('json'):
                    result_text = result_text[4:]
            result_text = result_text.strip()

        result = json.loads(result_text)
        adjust_link = result.get('adjust_link')

        if adjust_link:
            # Cache the found link
            cache_adjust_link(bybit_symbol, adjust_link)
            logger.info(f"AI found: {bybit_symbol} -> {adjust_link[:50]}...")
            return adjust_link
        else:
            # Cache as unavailable (empty string)
            cache_adjust_link(bybit_symbol, '')
            logger.info(f"AI: No Mudrex link for {bybit_symbol}")
            return None

    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse AI response for {bybit_symbol}: {e}")
        logger.debug(f"Response was: {result_text[:200] if result_text else 'empty'}")
        return None

    except Exception as e:
        logger.error(f"AI error for {bybit_symbol}: {e}")
        return None


def find_adjust_link_sync(bybit_symbol: str) -> Optional[str]:
    """
    Synchronous wrapper for find_adjust_link_with_ai
    For use in non-async contexts
    """
    import asyncio

    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # We're already in an async context
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(
                    asyncio.run,
                    find_adjust_link_with_ai(bybit_symbol)
                )
                return future.result(timeout=30)
        else:
            return loop.run_until_complete(find_adjust_link_with_ai(bybit_symbol))
    except Exception as e:
        logger.error(f"Sync wrapper error: {e}")
        return None
