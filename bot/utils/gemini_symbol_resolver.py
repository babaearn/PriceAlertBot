"""
Gemini 2.5 Flash symbol resolver
FREE TIER: 15 RPM, 20-50 RPD (plenty for our use case)

Batch processing: All symbols in ONE API call
"""

import os
import json
import logging
from typing import Dict, Optional, List

logger = logging.getLogger(__name__)

# Gemini API configuration
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
GEMINI_MODEL = 'gemini-2.5-flash'

# Initialize Gemini client
genai = None
model = None


def init_gemini():
    """Initialize Gemini API client"""
    global genai, model

    if not GEMINI_API_KEY:
        logger.warning("GEMINI_API_KEY not set, AI resolution disabled")
        return False

    try:
        import google.generativeai as genai_module
        genai_module.configure(api_key=GEMINI_API_KEY)
        genai = genai_module
        model = genai.GenerativeModel(
            GEMINI_MODEL,
            generation_config={
                'temperature': 0.1,  # Low temp for consistency
            }
        )
        logger.info("Gemini AI initialized")
        return True
    except ImportError:
        logger.warning("google-generativeai not installed, AI resolution disabled")
        return False
    except Exception as e:
        logger.error(f"Failed to initialize Gemini: {e}")
        return False


def is_gemini_available() -> bool:
    """Check if Gemini API is available"""
    return GEMINI_API_KEY is not None and GEMINI_API_KEY != ''


def batch_resolve_symbols(mudrex_symbols: List[str], bybit_symbols: List[str]) -> Dict[str, Optional[str]]:
    """
    Resolve ALL symbols in ONE API call (batch processing)

    FREE TIER: This uses 1 request out of 20-50 daily limit

    Args:
        mudrex_symbols: List of Mudrex symbols to map
        bybit_symbols: List of available Bybit symbols

    Returns:
        Dictionary of {mudrex_symbol: bybit_symbol or None}
    """
    global model

    if model is None:
        if not init_gemini():
            return {}

    # Prepare the prompt with all symbols
    prompt = f"""You are a cryptocurrency symbol mapping expert. Map these Mudrex symbols to Bybit equivalents.

**MUDREX SYMBOLS ({len(mudrex_symbols)} total):**
{json.dumps(mudrex_symbols, indent=2)}

**BYBIT SYMBOLS (sample of {min(200, len(bybit_symbols))}):**
{json.dumps(bybit_symbols[:200], indent=2)}

**MAPPING PATTERNS:**
1. Direct match: BTC/USDT → BTC/USDT
2. Multiplier prefixes: SHIB1000/USDT → 1000SHIB/USDT (move number to front)
3. Rebrands: MATIC/USDT → POL/USDT (Polygon rebrand)
4. Mergers: AGIX/USDT → FET/USDT (merged into Fetch.ai)
5. Different naming: RAYDIUM/USDT → RAY/USDT
6. Unavailable: STG/USDT → null (not on Bybit)

**OUTPUT FORMAT:**
Return ONLY valid JSON (no markdown, no code blocks), mapping each Mudrex symbol to its Bybit equivalent or null:
{{
  "BTC/USDT": "BTC/USDT",
  "SHIB1000/USDT": "1000SHIB/USDT",
  "STG/USDT": null
}}

Map all {len(mudrex_symbols)} symbols now:"""

    try:
        logger.info(f"🧠 Gemini: Batch resolving {len(mudrex_symbols)} symbols...")

        response = model.generate_content(prompt)
        result_text = response.text.strip()

        # Clean markdown code blocks if present
        if '```' in result_text:
            # Extract content between code blocks
            parts = result_text.split('```')
            if len(parts) >= 2:
                result_text = parts[1]
                # Remove language identifier if present
                if result_text.startswith('json'):
                    result_text = result_text[4:]
                result_text = result_text.strip()

        # Parse JSON
        mappings = json.loads(result_text)

        # Validate and log stats
        available = sum(1 for v in mappings.values() if v is not None)
        unavailable = sum(1 for v in mappings.values() if v is None)
        needs_mapping = sum(1 for k, v in mappings.items() if v and k != v)

        logger.info(
            f"🧠 Gemini complete: {available} available, {unavailable} unavailable, {needs_mapping} mapped"
        )

        return mappings

    except json.JSONDecodeError as e:
        logger.error(f"🧠 Gemini returned invalid JSON: {e}")
        logger.debug(f"Raw response: {result_text[:500]}...")
        return {}
    except Exception as e:
        logger.error(f"🧠 Gemini API error: {e}")
        return {}


def resolve_single_symbol(mudrex_symbol: str, bybit_symbols: List[str]) -> Optional[str]:
    """
    Resolve a single symbol (for new pairs)
    FREE TIER: Uses 1 request

    Args:
        mudrex_symbol: Single symbol to resolve
        bybit_symbols: List of available Bybit symbols

    Returns:
        Bybit symbol or None if unavailable
    """
    result = batch_resolve_symbols([mudrex_symbol], bybit_symbols)
    return result.get(mudrex_symbol)


# Legacy function for compatibility with old code
def auto_generate_mappings(mudrex_symbols: List[str], bybit_symbols: List[str],
                           progress_callback=None) -> Dict[str, Optional[str]]:
    """
    Legacy wrapper for batch_resolve_symbols
    Maintained for backward compatibility
    """
    return batch_resolve_symbols(mudrex_symbols, bybit_symbols)
