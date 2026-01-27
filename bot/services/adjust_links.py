"""
Adjust Deeplink Lookup with Comprehensive Diagnostics
"""
import json
import logging
import os
from pathlib import Path
from typing import Optional, Dict

logger = logging.getLogger(__name__)

# Global cache
adjust_links_cache: Dict[str, str] = {}
_diagnostics_run = False


def run_diagnostics():
    """
    Run comprehensive diagnostics on adjust links file
    This runs ONCE at startup to identify issues
    """
    global _diagnostics_run

    if _diagnostics_run:
        return

    _diagnostics_run = True

    logger.info("=" * 60)
    logger.info("🔍 VERIFYING ADJUST LINKS JSON FILE")
    logger.info("=" * 60)

    # Check multiple possible locations
    possible_paths = [
        Path(__file__).parent.parent.parent / 'data' / 'adjust_links.json',  # Standard location
        Path('/app/data/adjust_links.json'),  # Docker absolute path
        Path('./data/adjust_links.json'),  # Relative to current directory
        Path('data/adjust_links.json'),  # Relative without ./
        Path('/app/adjust_links.json'),  # Root of container
    ]

    logger.info(f"📁 Checking {len(possible_paths)} possible file locations:")

    for idx, path in enumerate(possible_paths, 1):
        abs_path = path.resolve()
        exists = path.exists()
        is_file = path.is_file() if exists else False

        logger.info(f"\n{idx}. {path}")
        logger.info(f"   Absolute: {abs_path}")
        logger.info(f"   Exists: {'✅ YES' if exists else '❌ NO'}")

        if exists:
            logger.info(f"   Is file: {'✅ YES' if is_file else '❌ NO (directory)'}")

            if is_file:
                try:
                    size = path.stat().st_size
                    logger.info(f"   Size: {size} bytes")

                    # Try to read it
                    with open(path, 'r') as f:
                        content = f.read()
                        logger.info(f"   Content length: {len(content)} chars")

                        # Try to parse JSON
                        data = json.loads(content)
                        logger.info(f"   JSON valid: ✅ YES")
                        logger.info(f"   Entries: {len(data)} adjust links")

                        # Show first 3 entries
                        logger.info(f"   Sample entries:")
                        for entry in data[:3]:
                            symbol = entry.get('symbol', 'N/A')
                            link = entry.get('adjust_link', 'N/A')
                            logger.info(f"      - {symbol}: {link}")

                        return path  # Found working file!

                except json.JSONDecodeError as e:
                    logger.error(f"   JSON invalid: ❌ {e}")
                except Exception as e:
                    logger.error(f"   Read error: ❌ {e}")

    # If we get here, no file was found
    logger.error("\n" + "=" * 60)
    logger.error("❌ ADJUST LINKS FILE NOT FOUND IN ANY LOCATION")
    logger.error("=" * 60)

    # Show current directory contents
    logger.info("\n📂 Current working directory: " + os.getcwd())
    logger.info("📂 Directory contents:")

    try:
        for item in sorted(os.listdir('.')):
            item_path = Path(item)
            item_type = "📁 DIR " if item_path.is_dir() else "📄 FILE"
            logger.info(f"   {item_type}: {item}")
    except Exception as e:
        logger.error(f"   Cannot list directory: {e}")

    # Check if data/ directory exists
    logger.info("\n📂 Checking 'data/' directory:")
    data_dir = Path('data')

    if data_dir.exists():
        logger.info(f"   ✅ data/ directory exists")
        logger.info(f"   Contents:")

        try:
            for item in sorted(data_dir.iterdir()):
                item_type = "📁 DIR " if item.is_dir() else "📄 FILE"
                logger.info(f"      {item_type}: {item.name}")
        except Exception as e:
            logger.error(f"      Cannot list: {e}")
    else:
        logger.error(f"   ❌ data/ directory does NOT exist")

    logger.info("\n" + "=" * 60)
    logger.info("💡 SOLUTIONS:")
    logger.info("=" * 60)
    logger.info("1. Ensure data/adjust_links.json is in your repository")
    logger.info("2. Check your Dockerfile COPY commands")
    logger.info("3. Verify file is not in .dockerignore")
    logger.info("4. Use absolute path in Docker: COPY data/ /app/data/")
    logger.info("=" * 60 + "\n")

    return None


def smart_find_file() -> Optional[Path]:
    """
    Smart file finder with multiple search strategies
    """
    logger.info("🔍 Searching for adjust_links.json...")

    # Strategy 1: Standard paths
    search_paths = [
        Path(__file__).parent.parent.parent / 'data' / 'adjust_links.json',
        Path('/app/data/adjust_links.json'),
        Path('./data/adjust_links.json'),
        Path('data/adjust_links.json'),
        Path('/app/adjust_links.json'),
        Path('./adjust_links.json'),
    ]

    for path in search_paths:
        if path.exists() and path.is_file():
            logger.info(f"✅ Found file: {path}")
            return path

    # Strategy 2: Walk up directory tree
    logger.info("🔍 Searching parent directories...")
    current = Path('.').resolve()

    for _ in range(5):  # Search up 5 levels
        candidate = current / 'data' / 'adjust_links.json'
        if candidate.exists():
            logger.info(f"✅ Found file: {candidate}")
            return candidate

        current = current.parent

    # Strategy 3: Search entire /app directory
    logger.info("🔍 Searching /app directory recursively...")
    app_dir = Path('/app')

    if app_dir.exists():
        try:
            for file_path in app_dir.rglob('adjust_links.json'):
                logger.info(f"✅ Found file: {file_path}")
                return file_path
        except Exception as e:
            logger.error(f"Recursive search failed: {e}")

    logger.error("❌ File not found after exhaustive search")
    return None


def load_adjust_links() -> bool:
    """
    Load adjust links from JSON file into memory cache
    Returns: True if successful, False otherwise
    """
    global adjust_links_cache

    logger.info("\n" + "=" * 60)
    logger.info("📥 LOADING ADJUST LINKS")
    logger.info("=" * 60)

    # Run diagnostics first
    file_path = run_diagnostics()

    # If diagnostics didn't find it, try smart search
    if file_path is None:
        logger.info("\n🔍 Running smart file finder...")
        file_path = smart_find_file()

    if file_path is None:
        logger.error("❌ Cannot load adjust links - file not found")
        logger.error("⚠️  Bot will continue but NO ALERTS will have adjust links!")
        return False

    try:
        logger.info(f"📂 Loading from: {file_path}")

        with open(file_path, 'r') as f:
            data = json.load(f)

        logger.info(f"✅ JSON parsed: {len(data)} entries")

        # Build cache with multiple symbol formats
        adjust_links_cache.clear()
        loaded_count = 0

        for entry in data:
            symbol = entry.get('symbol', '')
            link = entry.get('adjust_link', '')

            if not symbol or not link:
                logger.warning(f"⚠️  Skipping invalid entry: {entry}")
                continue

            # Store primary format
            adjust_links_cache[symbol] = link
            loaded_count += 1

            # Also store normalized formats
            # If "BTC/USDT", also store "BTCUSDT"
            if '/' in symbol:
                symbol_no_slash = symbol.replace('/', '')
                adjust_links_cache[symbol_no_slash] = link

            # If "BTCUSDT", also try "BTC/USDT"
            elif symbol.endswith('USDT') and len(symbol) > 4:
                symbol_with_slash = symbol[:-4] + '/USDT'
                adjust_links_cache[symbol_with_slash] = link

        logger.info(f"✅ Loaded {loaded_count} adjust links")
        logger.info(f"✅ Cache size: {len(adjust_links_cache)} entries (including normalized)")

        # Show sample
        logger.info("\n📊 Sample adjust links:")
        for idx, (symbol, link) in enumerate(list(adjust_links_cache.items())[:5], 1):
            logger.info(f"   {idx}. {symbol}: {link}")

        logger.info("=" * 60 + "\n")

        return True

    except json.JSONDecodeError as e:
        logger.error(f"❌ JSON parsing error: {e}")
        logger.error(f"   File: {file_path}")
        return False

    except Exception as e:
        logger.error(f"❌ Error loading adjust links: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False


def find_adjust_link(symbol: str) -> Optional[str]:
    """
    Find adjust link for a symbol with fuzzy matching

    Args:
        symbol: Trading pair like "BTC/USDT" or "BTCUSDT"

    Returns:
        Adjust link URL or None
    """
    # Direct lookup
    if symbol in adjust_links_cache:
        link = adjust_links_cache[symbol]
        logger.debug(f"✅ Found adjust link: {symbol} -> {link}")
        return link

    # Try without slash
    if '/' in symbol:
        symbol_no_slash = symbol.replace('/', '')
        if symbol_no_slash in adjust_links_cache:
            link = adjust_links_cache[symbol_no_slash]
            logger.debug(f"✅ Found adjust link: {symbol} (as {symbol_no_slash}) -> {link}")
            return link

    # Try with slash
    if '/' not in symbol and symbol.endswith('USDT'):
        symbol_with_slash = symbol[:-4] + '/USDT'
        if symbol_with_slash in adjust_links_cache:
            link = adjust_links_cache[symbol_with_slash]
            logger.debug(f"✅ Found adjust link: {symbol} (as {symbol_with_slash}) -> {link}")
            return link

    # Try case variations
    symbol_upper = symbol.upper()
    if symbol_upper in adjust_links_cache:
        link = adjust_links_cache[symbol_upper]
        logger.debug(f"✅ Found adjust link: {symbol} (as {symbol_upper}) -> {link}")
        return link

    logger.warning(f"⚠️  No adjust link found for: {symbol}")
    logger.debug(f"   Cache has {len(adjust_links_cache)} entries")

    # Show similar symbols for debugging
    similar = [s for s in adjust_links_cache.keys() if symbol.replace('/', '').upper() in s.upper()]
    if similar:
        logger.debug(f"   Similar symbols in cache: {similar[:5]}")

    return None


def get_cache_stats() -> dict:
    """Get statistics about the adjust links cache"""
    return {
        'total_entries': len(adjust_links_cache),
        'sample_symbols': list(adjust_links_cache.keys())[:10],
        'cache_loaded': len(adjust_links_cache) > 0
    }


# Load links when module is imported
logger.info("🚀 Initializing adjust_links module...")
load_success = load_adjust_links()

if load_success:
    logger.info("✅ Adjust links module initialized successfully")
else:
    logger.error("❌ Adjust links module initialization FAILED")
    logger.error("⚠️  Alerts will NOT include adjust links!")
