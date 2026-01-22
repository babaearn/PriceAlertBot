"""
Bot Configuration with Environment Validation
"""

import os
import sys
from dotenv import load_dotenv

load_dotenv()


def validate_env_vars():
    """Validate all required environment variables before starting"""
    required_vars = [
        'TELEGRAM_BOT_TOKEN',
        'TELEGRAM_GROUP_ID',
        'PRICE_ALERTS_TOPIC_ID',
        'DATABASE_URL',
        'ADMIN_USER_IDS'
    ]

    missing = [var for var in required_vars if not os.getenv(var)]

    if missing:
        print(f"❌ ERROR: Missing environment variables: {', '.join(missing)}")
        sys.exit(1)

    print("✅ All required environment variables present")


# Run validation
validate_env_vars()

# Telegram Configuration
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
TELEGRAM_GROUP_ID = int(os.getenv('TELEGRAM_GROUP_ID'))
PRICE_ALERTS_TOPIC_ID = int(os.getenv('PRICE_ALERTS_TOPIC_ID'))

# Parse admin IDs
admin_ids_str = os.getenv('ADMIN_USER_IDS', '')
ADMIN_USER_IDS = [int(x.strip()) for x in admin_ids_str.split(',') if x.strip()]

# Database Configuration
DATABASE_URL = os.getenv('DATABASE_URL')

# Fix Railway's postgres:// to postgresql:// for SQLAlchemy
if DATABASE_URL and DATABASE_URL.startswith('postgres://'):
    DATABASE_URL = DATABASE_URL.replace('postgres://', 'postgresql://', 1)

# Scanning Settings (REST API)
SCAN_INTERVAL = int(os.getenv('SCAN_INTERVAL', '30'))  # seconds
BATCH_SIZE = 50  # pairs per batch request
PRICE_CACHE_TTL = 10  # seconds

# Alert Thresholds
GAINER_THRESHOLDS = [10, 30, 60, 80, 100] + list(range(150, 1000, 50))
LOSER_THRESHOLDS = [-10, -30, -60, -80, -100] + list(range(-150, -1000, -50))

# Filters
MIN_VOLUME_24H = int(os.getenv('MIN_VOLUME_USD', '5000000'))  # $5M
COOLDOWN_MINUTES = 0  # Default: no cooldown

# Session Reset
SESSION_RESET_HOUR_UTC = 0  # 00:00 UTC

# API Settings (REST API via CCXT)
BYBIT_TIMEOUT = 10000  # milliseconds
BINANCE_TIMEOUT = 10000
MAX_API_RETRIES = 3
RETRY_DELAY = 2  # seconds

# Logging
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
LOG_FILE = 'scanner_bot.log'

# Pairs to skip (no Adjust links)
SKIP_PAIRS = {
    'APEX/USDT', 'SPX/USDT', 'AVNT/USDT', 'OPEN/USDT', 'STBL/USDT', 'ZKC/USDT',
    'Q/USDT', 'XPIN/USDT', 'UB/USDT', 'HOLO/USDT', 'OKB/USDT', 'BARD/USDT',
    'ASTER/USDT', '0G/USDT', 'FLUID/USDT', 'BLESS/USDT', 'HEMI/USDT', 'XPL/USDT',
    'NOM/USDT', 'MIRA/USDT', 'AKE/USDT', 'RLUSD/USDT', 'LIGHT/USDT', 'XAN/USDT',
    'FF/USDT', 'EDEN/USDT', 'VFY/USDT', 'TRUTH/USDT', 'COAI/USDT', '2Z/USDT',
    'KGEN/USDT', '4/USDT', 'GIGGLE/USDT', 'MET/USDT', 'YB/USDT', 'EUL/USDT',
    'ENSO/USDT', 'RECALL/USDT', 'CLO/USDT', 'HANA/USDT', 'EVAA/USDT', 'ZBT/USDT',
    'RIVER/USDT', 'TURTLE/USDT', 'APR/USDT', 'BLUAI/USDT', 'LAB/USDT', 'COMMON/USDT',
    'AT/USDT', 'MMT/USDT', 'KITE/USDT', 'CC/USDT', 'TRUST/USDT', 'ALLO/USDT',
    'PIEVERSE/USDT', 'UAI/USDT', 'JCT/USDT', 'BEAT/USDT', 'BOBBOB/USDT', 'IRYS/USDT',
    'RLS/USDT', 'NIGHT/USDT', 'FOLKS/USDT', 'STABLE/USDT', 'WET/USDT', 'CYS/USDT',
    'US/USDT', 'RAVE/USDT', 'ZKP/USDT', 'FOGO/USDT'
}

print(f"""
🤖 Bot Configuration:
- Scan Interval: {SCAN_INTERVAL}s (REST API)
- Batch Size: {BATCH_SIZE} pairs
- Min Volume: ${MIN_VOLUME_24H:,}
- Admins: {len(ADMIN_USER_IDS)}
- Database: {'✅' if DATABASE_URL else '❌'}
- Skip Pairs: {len(SKIP_PAIRS)} pairs without Adjust links
""")
