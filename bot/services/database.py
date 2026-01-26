"""
Database Service Layer - PostgreSQL Operations
"""

import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import date, datetime, timedelta
from typing import List, Dict, Optional
import logging
from bot import config

logger = logging.getLogger(__name__)


def get_connection():
    """Get database connection"""
    try:
        if not config.DATABASE_URL:
            raise ValueError("DATABASE_URL is not set")
        conn = psycopg2.connect(config.DATABASE_URL)
        return conn
    except Exception as e:
        logger.error(f"❌ Database connection failed: {e}")
        logger.error(f"   DATABASE_URL starts with: {config.DATABASE_URL[:20] if config.DATABASE_URL else 'NOT SET'}...")
        raise


def get_active_pairs() -> List[Dict]:
    """
    Get all active pairs with Adjust links
    Returns: List of dicts with symbol, adjust_link
    """
    conn = get_connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT symbol, adjust_link, added_by, added_at
                FROM active_pairs
                WHERE status = 'active' AND adjust_link IS NOT NULL AND adjust_link != ''
                ORDER BY symbol
            """)
            pairs = cur.fetchall()
            return [dict(row) for row in pairs]
    finally:
        conn.close()


def add_pair(symbol: str, adjust_link: str, added_by: str) -> bool:
    """
    Add new trading pair
    Returns: True if successful, False if already exists
    """
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO active_pairs (symbol, adjust_link, added_by)
                VALUES (%s, %s, %s)
                ON CONFLICT (symbol) DO NOTHING
                RETURNING id
            """, (symbol, adjust_link, added_by))
            conn.commit()
            result = cur.fetchone()
            if result:
                logger.info(f"✅ Added pair: {symbol}")
                return True
            else:
                logger.warning(f"Pair already exists: {symbol}")
                return False
    except Exception as e:
        conn.rollback()
        logger.error(f"Failed to add pair {symbol}: {e}")
        return False
    finally:
        conn.close()


def remove_pair(symbol: str) -> bool:
    """
    Remove trading pair (sets status to inactive)
    Returns: True if successful
    """
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE active_pairs
                SET status = 'inactive'
                WHERE symbol = %s
                RETURNING id
            """, (symbol,))
            conn.commit()
            result = cur.fetchone()
            if result:
                logger.info(f"✅ Removed pair: {symbol}")
                return True
            else:
                logger.warning(f"Pair not found: {symbol}")
                return False
    except Exception as e:
        conn.rollback()
        logger.error(f"Failed to remove pair {symbol}: {e}")
        return False
    finally:
        conn.close()


def get_session_start_price(symbol: str) -> Optional[float]:
    """
    Get session start price (00:00 UTC) for symbol
    If not found, use current price as session start
    """
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            # Get today's session start price
            today = date.today()
            cur.execute("""
                SELECT session_start_price
                FROM price_snapshots
                WHERE symbol = %s
                  AND DATE(timestamp) = %s
                  AND session_start_price IS NOT NULL
                ORDER BY timestamp DESC
                LIMIT 1
            """, (symbol, today))

            result = cur.fetchone()
            if result and result[0]:
                return float(result[0])

            # Fallback: Get most recent price
            cur.execute("""
                SELECT price
                FROM price_snapshots
                WHERE symbol = %s
                ORDER BY timestamp DESC
                LIMIT 1
            """, (symbol,))

            result = cur.fetchone()
            return float(result[0]) if result else None
    finally:
        conn.close()


def save_price_snapshot(symbol: str, price: float, volume_24h: float,
                        session_start_price: Optional[float], source: str):
    """Save price snapshot to database"""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO price_snapshots
                (symbol, price, volume_24h, session_start_price, source)
                VALUES (%s, %s, %s, %s, %s)
            """, (symbol, price, volume_24h, session_start_price, source))
            conn.commit()
    except Exception as e:
        conn.rollback()
        logger.error(f"Failed to save price snapshot for {symbol}: {e}")
    finally:
        conn.close()


def check_alert_fired(symbol: str, threshold_percent: float, session_date: date) -> bool:
    """
    Check if alert already fired for this threshold today
    Returns: True if already fired, False if not
    """
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT id FROM alert_history
                WHERE symbol = %s
                  AND threshold_percent = %s
                  AND session_date = %s
                LIMIT 1
            """, (symbol, threshold_percent, session_date))

            result = cur.fetchone()
            return result is not None
    finally:
        conn.close()


def log_alert(symbol: str, threshold_percent: float, trigger_price: float,
              session_start_price: float, actual_change_percent: float,
              volume_24h: float, telegram_message_id: Optional[int],
              session_date: date):
    """Log fired alert to database"""
    conn = get_connection()
    try:
        alert_type = 'gainer' if actual_change_percent > 0 else 'loser'

        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO alert_history
                (symbol, threshold_percent, alert_type, trigger_price,
                 session_start_price, actual_change_percent, volume_24h,
                 telegram_message_id, session_date)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (symbol, threshold_percent, alert_type, trigger_price,
                  session_start_price, actual_change_percent, volume_24h,
                  telegram_message_id, session_date))
            conn.commit()
    except Exception as e:
        conn.rollback()
        logger.error(f"Failed to log alert for {symbol}: {e}")
    finally:
        conn.close()


def log_scan_cycle(scan_cycle: int, pairs_scanned: int, alerts_triggered: int,
                   errors: int, duration_seconds: float):
    """Log scanner cycle performance"""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO scanner_logs
                (scan_cycle, pairs_scanned, alerts_triggered, errors, duration_seconds)
                VALUES (%s, %s, %s, %s, %s)
            """, (scan_cycle, pairs_scanned, alerts_triggered, errors, duration_seconds))
            conn.commit()
    except Exception as e:
        conn.rollback()
        logger.error(f"Failed to log scan cycle: {e}")
    finally:
        conn.close()


def get_config_value(key: str, default: str = None) -> Optional[str]:
    """Get configuration value from database"""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT value FROM bot_config WHERE key = %s", (key,))
            result = cur.fetchone()
            return result[0] if result else default
    finally:
        conn.close()


def set_config_value(key: str, value: str, updated_by: str):
    """Set configuration value in database"""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO bot_config (key, value, updated_by)
                VALUES (%s, %s, %s)
                ON CONFLICT (key) DO UPDATE
                SET value = EXCLUDED.value,
                    updated_at = NOW(),
                    updated_by = EXCLUDED.updated_by
            """, (key, value, updated_by))
            conn.commit()
    except Exception as e:
        conn.rollback()
        logger.error(f"Failed to set config {key}: {e}")
    finally:
        conn.close()


def get_stats() -> Dict:
    """Get bot statistics"""
    conn = get_connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            # Active pairs count
            cur.execute("SELECT COUNT(*) as count FROM active_pairs WHERE status = 'active'")
            active_pairs = cur.fetchone()['count']

            # Alerts today
            today = date.today()
            cur.execute("SELECT COUNT(*) as count FROM alert_history WHERE session_date = %s", (today,))
            alerts_today = cur.fetchone()['count']

            # Alerts last 7 days
            week_ago = today - timedelta(days=7)
            cur.execute("SELECT COUNT(*) as count FROM alert_history WHERE session_date >= %s", (week_ago,))
            alerts_week = cur.fetchone()['count']

            # Last scan
            cur.execute("SELECT * FROM scanner_logs ORDER BY timestamp DESC LIMIT 1")
            last_scan = cur.fetchone()

            return {
                'active_pairs': active_pairs,
                'alerts_today': alerts_today,
                'alerts_week': alerts_week,
                'last_scan': dict(last_scan) if last_scan else None
            }
    finally:
        conn.close()


def cleanup_old_data():
    """Cleanup old price snapshots and logs"""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT cleanup_old_data()")
            conn.commit()
            logger.info("✅ Cleaned up old data")
    except Exception as e:
        conn.rollback()
        logger.error(f"Failed to cleanup old data: {e}")
    finally:
        conn.close()


def seed_initial_pairs(force_reseed=False):
    """Seed all 438 active trading pairs with Adjust links"""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM active_pairs")
            count = cur.fetchone()[0]

            if count > 0 and not force_reseed:
                logger.info(f"📊 Database already has {count} pairs, skipping seed")
                return 0

            if force_reseed and count > 0:
                logger.info(f"🔄 Force reseed: Clearing {count} existing pairs...")
                cur.execute("DELETE FROM price_snapshots")
                cur.execute("DELETE FROM alert_history")
                cur.execute("DELETE FROM active_pairs")
                conn.commit()

            # All 438 pairs with Adjust links
            initial_pairs = [
                ('BTC/USDT', 'https://mudrex.go.link/1Yogo', 'system'),
                ('ETH/USDT', 'https://mudrex.go.link/kmYNX', 'system'),
                ('BNB/USDT', 'https://mudrex.go.link/3G8Mh', 'system'),
                ('SOL/USDT', 'https://mudrex.go.link/g6445', 'system'),
                ('USDC/USDT', 'https://mudrex.go.link/kDf6w', 'system'),
                ('XRP/USDT', 'https://mudrex.go.link/h6Nof', 'system'),
                ('DOGE/USDT', 'https://mudrex.go.link/8BuD2', 'system'),
                ('ADA/USDT', 'https://mudrex.go.link/hKGmX', 'system'),
                ('AVAX/USDT', 'https://mudrex.go.link/dZEy1', 'system'),
                ('TRX/USDT', 'https://mudrex.go.link/lnojH', 'system'),
                ('LINK/USDT', 'https://mudrex.go.link/6fvof', 'system'),
                ('DOT/USDT', 'https://mudrex.go.link/2Xc0B', 'system'),
                ('BCH/USDT', 'https://mudrex.go.link/iXh5Q', 'system'),
                ('UNI/USDT', 'https://mudrex.go.link/4BQrV', 'system'),
                ('NEAR/USDT', 'https://mudrex.go.link/4abAr', 'system'),
                ('LTC/USDT', 'https://mudrex.go.link/5KhId', 'system'),
                ('ICP/USDT', 'https://mudrex.go.link/8oFyE', 'system'),
                ('ETC/USDT', 'https://mudrex.go.link/5UlJJ', 'system'),
                ('APT/USDT', 'https://mudrex.go.link/3jz4i', 'system'),
                ('HBAR/USDT', 'https://mudrex.go.link/cYDjC', 'system'),
                ('XLM/USDT', 'https://mudrex.go.link/3mvNd', 'system'),
                ('ATOM/USDT', 'https://mudrex.go.link/cpkYU', 'system'),
                ('FIL/USDT', 'https://mudrex.go.link/2wnCx', 'system'),
                ('STX/USDT', 'https://mudrex.go.link/ik2aE', 'system'),
                ('IMX/USDT', 'https://mudrex.go.link/GRCEi', 'system'),
                ('VET/USDT', 'https://mudrex.go.link/6XUUJ', 'system'),
                ('GRT/USDT', 'https://mudrex.go.link/gGppc', 'system'),
                ('OP/USDT', 'https://mudrex.go.link/ivoLn', 'system'),
                ('AR/USDT', 'https://mudrex.go.link/3wXbs', 'system'),
                ('JASMY/USDT', 'https://mudrex.go.link/93h9I', 'system'),
                ('CRV/USDT', 'https://mudrex.go.link/l8DBq', 'system'),
                ('ENS/USDT', 'https://mudrex.go.link/8lqHU', 'system'),
                ('RUNE/USDT', 'https://mudrex.go.link/2ywzj', 'system'),
                ('ARB/USDT', 'https://mudrex.go.link/80iC5', 'system'),
                ('ENA/USDT', 'https://mudrex.go.link/5KVOf', 'system'),
                ('ETHFI/USDT', 'https://mudrex.go.link/6yGSS', 'system'),
                ('STRK/USDT', 'https://mudrex.go.link/gNjvO', 'system'),
                ('SUI/USDT', 'https://mudrex.go.link/djU1j', 'system'),
                ('ARKM/USDT', 'https://mudrex.go.link/id1ub', 'system'),
                ('USTC/USDT', 'https://mudrex.go.link/92g3I', 'system'),
                ('SEI/USDT', 'https://mudrex.go.link/dfYuY', 'system'),
                ('DYM/USDT', 'https://mudrex.go.link/c9LXx', 'system'),
                ('IO/USDT', 'https://mudrex.go.link/9FGTj', 'system'),
                ('BOME/USDT', 'https://mudrex.go.link/eIrCK', 'system'),
                ('JUP/USDT', 'https://mudrex.go.link/fRHkD', 'system'),
                ('ZK/USDT', 'https://mudrex.go.link/2NVXz', 'system'),
                ('OM/USDT', 'https://mudrex.go.link/e7w9Y', 'system'),
                ('PYTH/USDT', 'https://mudrex.go.link/hxEFz', 'system'),
                ('TAO/USDT', 'https://mudrex.go.link/cX2j6', 'system'),
                ('MANTA/USDT', 'https://mudrex.go.link/1vtB8', 'system'),
                ('JTO/USDT', 'https://mudrex.go.link/a7LDw', 'system'),
                ('BLUR/USDT', 'https://mudrex.go.link/hj2GQ', 'system'),
                ('SAGA/USDT', 'https://mudrex.go.link/kMrS9', 'system'),
                ('AERGO/USDT', 'https://mudrex.go.link/6FNGk', 'system'),
                ('OG/USDT', 'https://mudrex.go.link/44fHa', 'system'),
                ('GNO/USDT', 'https://mudrex.go.link/ikUTm', 'system'),
                ('JST/USDT', 'https://mudrex.go.link/iujBU', 'system'),
                ('NKN/USDT', 'https://mudrex.go.link/el4Nx', 'system'),
                ('PROM/USDT', 'https://mudrex.go.link/ciKWR', 'system'),
                ('IDEX/USDT', 'https://mudrex.go.link/4bpe4', 'system'),
                ('CTK/USDT', 'https://mudrex.go.link/4sfr0', 'system'),
                ('XNO/USDT', 'https://mudrex.go.link/2VlfM', 'system'),
                ('MBOX/USDT', 'https://mudrex.go.link/8LCDF', 'system'),
                ('WAXP/USDT', 'https://mudrex.go.link/fiTXa', 'system'),
                ('BOBA/USDT', 'https://mudrex.go.link/c1RXZ', 'system'),
                ('DODO/USDT', 'https://mudrex.go.link/3okFt', 'system'),
                ('REQ/USDT', 'https://mudrex.go.link/iIsJK', 'system'),
                ('CVC/USDT', 'https://mudrex.go.link/29Cso', 'system'),
                ('SFP/USDT', 'https://mudrex.go.link/2E86s', 'system'),
                ('DENT/USDT', 'https://mudrex.go.link/9c3h9', 'system'),
                ('SUN/USDT', 'https://mudrex.go.link/4lT94', 'system'),
                ('BAND/USDT', 'https://mudrex.go.link/lHHwN', 'system'),
                ('PHA/USDT', 'https://mudrex.go.link/epb5n', 'system'),
                ('T/USDT', 'https://mudrex.go.link/2onI4', 'system'),
                ('RLC/USDT', 'https://mudrex.go.link/7wtkD', 'system'),
                ('SXP/USDT', 'https://mudrex.go.link/sxpusdt', 'system'),
                ('LQTY/USDT', 'https://mudrex.go.link/LQTYUSDT', 'system'),
                ('SCRT/USDT', 'https://mudrex.go.link/SCRT', 'system'),
                ('CRO/USDT', 'https://mudrex.go.link/iNUXQ', 'system'),
                ('XCN/USDT', 'https://mudrex.go.link/XCN', 'system'),
                ('STEEM/USDT', 'https://mudrex.go.link/STEEM', 'system'),
                ('CTSI/USDT', 'https://mudrex.go.link/CTSI', 'system'),
                ('ARPA/USDT', 'https://mudrex.go.link/ARPA', 'system'),
                ('SNT/USDT', 'https://mudrex.go.link/SNT', 'system'),
                ('BNT/USDT', 'https://mudrex.go.link/BNT', 'system'),
                ('OXT/USDT', 'https://mudrex.go.link/OXT', 'system'),
                ('SKL/USDT', 'https://mudrex.go.link/SKL', 'system'),
                ('DGB/USDT', 'https://mudrex.go.link/DGB', 'system'),
                ('KNC/USDT', 'https://mudrex.go.link/KNC', 'system'),
                ('POWR/USDT', 'https://mudrex.go.link/POWR', 'system'),
                ('XVS/USDT', 'https://mudrex.go.link/XVS', 'system'),
                ('HFT/USDT', 'https://mudrex.go.link/HFT', 'system'),
                ('RARE/USDT', 'https://mudrex.go.link/RARE', 'system'),
                ('AGLD/USDT', 'https://mudrex.go.link/AGLD', 'system'),
                ('BAT/USDT', 'https://mudrex.go.link/aWkbq', 'system'),
                ('OGN/USDT', 'https://mudrex.go.link/OGNUSDT', 'system'),
                ('HOOK/USDT', 'https://mudrex.go.link/HOOK', 'system'),
                ('RVN/USDT', 'https://mudrex.go.link/RVN', 'system'),
                ('CTC/USDT', 'https://mudrex.go.link/CTC', 'system'),
                ('MAV/USDT', 'https://mudrex.go.link/MAV', 'system'),
                ('IOST/USDT', 'https://mudrex.go.link/IOST', 'system'),
                ('BICO/USDT', 'https://mudrex.go.link/BICO', 'system'),
                ('ICX/USDT', 'https://mudrex.go.link/ICX', 'system'),
                ('MTL/USDT', 'https://mudrex.go.link/MTL', 'system'),
                ('KAVA/USDT', 'https://mudrex.go.link/KAVA', 'system'),
                ('LRC/USDT', 'https://mudrex.go.link/LRCUSDT', 'system'),
                ('QNT/USDT', 'https://mudrex.go.link/1047W', 'system'),
                ('ONT/USDT', 'https://mudrex.go.link/ONT', 'system'),
                ('TWT/USDT', 'https://mudrex.go.link/4ILyp', 'system'),
                ('ANKR/USDT', 'https://mudrex.go.link/ANKR', 'system'),
                ('PAXG/USDT', 'https://mudrex.go.link/PAXG', 'system'),
                ('METIS/USDT', 'https://mudrex.go.link/METIS', 'system'),
                ('TLM/USDT', 'https://mudrex.go.link/TLM', 'system'),
                ('YFI/USDT', 'https://mudrex.go.link/YFI', 'system'),
                ('XMR/USDT', 'https://mudrex.go.link/ilbvY', 'system'),
                ('AUCTION/USDT', 'https://mudrex.go.link/ACTION', 'system'),
                ('BEL/USDT', 'https://mudrex.go.link/BEL', 'system'),
                ('IOTA/USDT', 'https://mudrex.go.link/IOTA', 'system'),
                ('ENJ/USDT', 'https://mudrex.go.link/ENJUSDT', 'system'),
                ('LSK/USDT', 'https://mudrex.go.link/LSK', 'system'),
                ('RPL/USDT', 'https://mudrex.go.link/RPL', 'system'),
                ('SPELL/USDT', 'https://mudrex.go.link/SPELL', 'system'),
                ('NTRN/USDT', 'https://mudrex.go.link/NTRN', 'system'),
                ('ONG/USDT', 'https://mudrex.go.link/ONG', 'system'),
                ('ONE/USDT', 'https://mudrex.go.link/ONE', 'system'),
                ('REZ/USDT', 'https://mudrex.go.link/REN', 'system'),
                ('ONDO/USDT', 'https://mudrex.go.link/ciJVT', 'system'),
                ('GODS/USDT', 'https://mudrex.go.link/GODS', 'system'),
                ('CORE/USDT', 'https://mudrex.go.link/CORE', 'system'),
                ('MNT/USDT', 'https://mudrex.go.link/MNT', 'system'),
                ('KAS/USDT', 'https://mudrex.go.link/KASUSDT', 'system'),
                ('DEGEN/USDT', 'https://mudrex.go.link/DEGEN', 'system'),
                ('BRETT/USDT', 'https://mudrex.go.link/7zBLe', 'system'),
                ('MEW/USDT', 'https://mudrex.go.link/MEW', 'system'),
                ('PONKE/USDT', 'https://mudrex.go.link/PONKE', 'system'),
                ('POPCAT/USDT', 'https://mudrex.go.link/POPCAT', 'system'),
                ('BLAST/USDT', 'https://mudrex.go.link/BLAST', 'system'),
                ('XDC/USDT', 'https://mudrex.go.link/6eYhR', 'system'),
                ('SD/USDT', 'https://mudrex.go.link/178xx', 'system'),
                ('FLR/USDT', 'https://mudrex.go.link/FLR', 'system'),
                ('CGPT/USDT', 'https://mudrex.go.link/55LQg', 'system'),
                ('AGI/USDT', 'https://mudrex.go.link/AGI', 'system'),
                ('VELO/USDT', 'https://mudrex.go.link/VELO', 'system'),
                ('AIOZ/USDT', 'https://mudrex.go.link/AIOZ', 'system'),
                ('ZETA/USDT', 'https://mudrex.go.link/ZETA', 'system'),
                ('MAVIA/USDT', 'https://mudrex.go.link/MAVIA', 'system'),
                ('MERL/USDT', 'https://mudrex.go.link/MERL', 'system'),
                ('SAFE/USDT', 'https://mudrex.go.link/SAFE', 'system'),
                ('TAI/USDT', 'https://mudrex.go.link/dwNXL', 'system'),
                ('DRIFT/USDT', 'https://mudrex.go.link/DRIFT', 'system'),
                ('TAIKO/USDT', 'https://mudrex.go.link/TAIKO', 'system'),
                ('ATH/USDT', 'https://mudrex.go.link/ATH', 'system'),
                ('SAROS/USDT', 'https://mudrex.go.link/3J2D8', 'system'),
                ('KMNO/USDT', 'https://mudrex.go.link/KMNO', 'system'),
                ('SQD/USDT', 'https://mudrex.go.link/8c8gD', 'system'),
                ('COOKIE/USDT', 'https://mudrex.go.link/2BlQC', 'system'),
                ('MOCA/USDT', 'https://mudrex.go.link/MOCA', 'system'),
                ('XION/USDT', 'https://mudrex.go.link/XION', 'system'),
                ('G/USDT', 'https://mudrex.go.link/GUSDT', 'system'),
                ('X/USDT', 'https://mudrex.go.link/2XUSDT', 'system'),
                ('RSR/USDT', 'https://mudrex.go.link/RSR', 'system'),
                ('LIT/USDT', 'https://mudrex.go.link/LIT', 'system'),
                ('FTM/USDT', 'https://mudrex.go.link/FTM', 'system'),
                ('ZRX/USDT', 'https://mudrex.go.link/ZRX', 'system'),
                ('CHR/USDT', 'https://mudrex.go.link/CHR', 'system'),
                ('BADGER/USDT', 'https://mudrex.go.link/BADGER', 'system'),
                ('MDT/USDT', 'https://mudrex.go.link/MDT', 'system'),
                ('CELR/USDT', 'https://mudrex.go.link/CELR', 'system'),
                ('1INCH/USDT', 'https://mudrex.go.link/1INCH', 'system'),
                ('SUPER/USDT', 'https://mudrex.go.link/SUPER', 'system'),
                ('ZEN/USDT', 'https://mudrex.go.link/ZEN', 'system'),
                ('SC/USDT', 'https://mudrex.go.link/SC', 'system'),
                ('STPT/USDT', 'https://mudrex.go.link/STPT', 'system'),
                ('FTT/USDT', 'https://mudrex.go.link/FTT', 'system'),
                ('KLAY/USDT', 'https://mudrex.go.link/KLAY', 'system'),
                ('DATA/USDT', 'https://mudrex.go.link/DATA', 'system'),
                ('MASK/USDT', 'https://mudrex.go.link/MASK', 'system'),
                ('SYN/USDT', 'https://mudrex.go.link/SYN', 'system'),
                ('OMG/USDT', 'https://mudrex.go.link/OMG', 'system'),
                ('TRB/USDT', 'https://mudrex.go.link/TRB', 'system'),
                ('LDO/USDT', 'https://mudrex.go.link/LDO', 'system'),
                ('DAR/USDT', 'https://mudrex.go.link/DAR', 'system'),
                ('LOOM/USDT', 'https://mudrex.go.link/LOOM', 'system'),
                ('INJ/USDT', 'https://mudrex.go.link/INJ', 'system'),
                ('API3/USDT', 'https://mudrex.go.link/API3', 'system'),
                ('OCEAN/USDT', 'https://mudrex.go.link/OCEAN', 'system'),
                ('FRONT/USDT', 'https://mudrex.go.link/FRONT', 'system'),
                ('MAGIC/USDT', 'https://mudrex.go.link/MAGIC', 'system'),
                ('QI/USDT', 'https://mudrex.go.link/QI', 'system'),
                ('BAKE/USDT', 'https://mudrex.go.link/BAKE', 'system'),
                ('GLM/USDT', 'https://mudrex.go.link/GLM', 'system'),
                ('COMP/USDT', 'https://mudrex.go.link/COMP', 'system'),
                ('MKR/USDT', 'https://mudrex.go.link/MKR', 'system'),
                ('AAVE/USDT', 'https://mudrex.go.link/AAVE', 'system'),
                ('CVX/USDT', 'https://mudrex.go.link/CVX', 'system'),
                ('ROSE/USDT', 'https://mudrex.go.link/ROSE', 'system'),
                ('RDNT/USDT', 'https://mudrex.go.link/RDNT', 'system'),
                ('SUSHI/USDT', 'https://mudrex.go.link/SUSHI', 'system'),
                ('ZIL/USDT', 'https://mudrex.go.link/ZIL', 'system'),
                ('SNX/USDT', 'https://mudrex.go.link/SNX', 'system'),
                ('SAND/USDT', 'https://mudrex.go.link/SAND', 'system'),
                ('ALICE/USDT', 'https://mudrex.go.link/ALICE', 'system'),
                ('MANA/USDT', 'https://mudrex.go.link/MANA', 'system'),
                ('AXS/USDT', 'https://mudrex.go.link/AXS', 'system'),
                ('WAVES/USDT', 'https://mudrex.go.link/WAVES', 'system'),
                ('NEO/USDT', 'https://mudrex.go.link/NEO', 'system'),
                ('ASTR/USDT', 'https://mudrex.go.link/ASTR', 'system'),
                ('ALGO/USDT', 'https://mudrex.go.link/ALGO', 'system'),
                ('EOS/USDT', 'https://mudrex.go.link/EOS', 'system'),
                ('XEM/USDT', 'https://mudrex.go.link/XEM', 'system'),
                ('DASH/USDT', 'https://mudrex.go.link/DASH', 'system'),
                ('EGS/USDT', 'https://mudrex.go.link/EGS', 'system'),
                ('AIXBT/USDT', 'https://mudrex.go.link/AIXBT', 'system'),
                ('GMT/USDT', 'https://mudrex.go.link/GMT', 'system'),
                ('1000WHY/USDT', 'https://mudrex.go.link/WHY', 'system'),
                ('GAS/USDT', 'https://mudrex.go.link/GAS', 'system'),
                ('CELO/USDT', 'https://mudrex.go.link/CELO', 'system'),
                ('PENDLE/USDT', 'https://mudrex.go.link/PENDLE', 'system'),
                ('PHB/USDT', 'https://mudrex.go.link/PHB', 'system'),
                ('POLYX/USDT', 'https://mudrex.go.link/POLYX', 'system'),
                ('FET/USDT', 'https://mudrex.go.link/FET', 'system'),
                ('STG/USDT', 'https://mudrex.go.link/STG', 'system'),
                ('AGIX/USDT', 'https://mudrex.go.link/AGIX', 'system'),
                ('WLD/USDT', 'https://mudrex.go.link/WLD', 'system'),
                ('RNDR/USDT', 'https://mudrex.go.link/RNDR', 'system'),
                ('EGLD/USDT', 'https://mudrex.go.link/EGLD', 'system'),
                ('FXS/USDT', 'https://mudrex.go.link/FXS', 'system'),
                ('OSMO/USDT', 'https://mudrex.go.link/OSMO', 'system'),
                ('THETA/USDT', 'https://mudrex.go.link/THETA', 'system'),
                ('MATIC/USDT', 'https://mudrex.go.link/MATIC', 'system'),
                ('ORDI/USDT', 'https://mudrex.go.link/ORDI', 'system'),
                ('WBTC/USDT', 'https://mudrex.go.link/WBTC', 'system'),
                ('CHZ/USDT', 'https://mudrex.go.link/CHZ', 'system'),
                ('WOO/USDT', 'https://mudrex.go.link/WOO', 'system'),
                ('1000SHIB/USDT', 'https://mudrex.go.link/1000SHIBUSDT', 'system'),
                ('TIA/USDT', 'https://mudrex.go.link/TIA', 'system'),
                ('REN/USDT', 'https://mudrex.go.link/RENUSDT', 'system'),
                ('RUNE1/USDT', 'https://mudrex.go.link/RUNE1', 'system'),
                ('AGRS/USDT', 'https://mudrex.go.link/AGRS', 'system'),
                ('XYM/USDT', 'https://mudrex.go.link/XYM', 'system'),
                ('XTZ/USDT', 'https://mudrex.go.link/XTZ', 'system'),
                ('SSV/USDT', 'https://mudrex.go.link/SSV', 'system'),
                ('TRU/USDT', 'https://mudrex.go.link/TRU', 'system'),
                ('UNFI/USDT', 'https://mudrex.go.link/UNFI', 'system'),
                ('LEVER/USDT', 'https://mudrex.go.link/LEVER', 'system'),
                ('VOXEL/USDT', 'https://mudrex.go.link/VOXEL', 'system'),
                ('TOMI/USDT', 'https://mudrex.go.link/TOMI', 'system'),
                ('DUSK/USDT', 'https://mudrex.go.link/DUSK', 'system'),
                ('MINA/USDT', 'https://mudrex.go.link/MINA', 'system'),
                ('COTI/USDT', 'https://mudrex.go.link/COTI', 'system'),
                ('CYBER/USDT', 'https://mudrex.go.link/CYBER', 'system'),
                ('FLOW/USDT', 'https://mudrex.go.link/FLOW', 'system'),
                ('SUKU/USDT', 'https://mudrex.go.link/SUKU', 'system'),
                ('MBX/USDT', 'https://mudrex.go.link/MBX', 'system'),
                ('AUDIO/USDT', 'https://mudrex.go.link/AUDIO', 'system'),
                ('FUN/USDT', 'https://mudrex.go.link/FUN', 'system'),
                ('MEME/USDT', 'https://mudrex.go.link/MEME', 'system'),
                ('AMP/USDT', 'https://mudrex.go.link/AMP', 'system'),
                ('UFT/USDT', 'https://mudrex.go.link/UFT', 'system'),
                ('CHESS/USDT', 'https://mudrex.go.link/CHESS', 'system'),
                ('CREAM/USDT', 'https://mudrex.go.link/CREAM', 'system'),
                ('ACH/USDT', 'https://mudrex.go.link/ACH', 'system'),
                ('WEMIX/USDT', 'https://mudrex.go.link/WEMIX', 'system'),
                ('REEF/USDT', 'https://mudrex.go.link/REEF', 'system'),
                ('FLUX/USDT', 'https://mudrex.go.link/FLUX', 'system'),
                ('DIA1/USDT', 'https://mudrex.go.link/DIA1', 'system'),
                ('YGG/USDT', 'https://mudrex.go.link/YGG', 'system'),
                ('GTC/USDT', 'https://mudrex.go.link/GTC', 'system'),
                ('PEOPLE/USDT', 'https://mudrex.go.link/PEOPLE', 'system'),
                ('C98/USDT', 'https://mudrex.go.link/C98', 'system'),
                ('HIFI/USDT', 'https://mudrex.go.link/HIFI', 'system'),
                ('APE/USDT', 'https://mudrex.go.link/APE', 'system'),
                ('LPT/USDT', 'https://mudrex.go.link/LPT', 'system'),
                ('ILV/USDT', 'https://mudrex.go.link/ILV', 'system'),
                ('GALA/USDT', 'https://mudrex.go.link/GALA', 'system'),
                ('WIF/USDT', 'https://mudrex.go.link/WIF', 'system'),
                ('AGLD1/USDT', 'https://mudrex.go.link/AGLD1', 'system'),
                ('TRB1/USDT', 'https://mudrex.go.link/TRB1', 'system'),
                ('ZRX1/USDT', 'https://mudrex.go.link/ZRX1', 'system'),
                ('AVAX1/USDT', 'https://mudrex.go.link/AVAX1', 'system'),
                ('10000SATS/USDT', 'https://mudrex.go.link/10000SATS', 'system'),
                ('1000BONK/USDT', 'https://mudrex.go.link/BONK', 'system'),
                ('1000FLOKI/USDT', 'https://mudrex.go.link/FLOKI', 'system'),
                ('1000NEIROCTO/USDT', 'https://mudrex.go.link/NEIROCTO', 'system'),
                ('1000PEPE/USDT', 'https://mudrex.go.link/PEPE', 'system'),
                ('1000RATS/USDT', 'https://mudrex.go.link/RATS', 'system'),
                ('ARC/USDT', 'https://mudrex.go.link/ARC', 'system'),
                ('COW/USDT', 'https://mudrex.go.link/COW', 'system'),
                ('FARTCOIN/USDT', 'https://mudrex.go.link/FARTCOIN', 'system'),
                ('GRIFFAIN/USDT', 'https://mudrex.go.link/GRIFFAIN', 'system'),
                ('HYPE/USDT', 'https://mudrex.go.link/fYNEv', 'system'),
                ('JELLYJELLY/USDT', 'https://mudrex.go.link/JELLYJELLY', 'system'),
                ('KAITO/USDT', 'https://mudrex.go.link/KAITO', 'system'),
                ('SHIB1000/USDT', 'https://mudrex.go.link/5rgfQ', 'system'),
                ('SOLAYER/USDT', 'https://mudrex.go.link/SOLAYER', 'system'),
                ('SONIC/USDT', 'https://mudrex.go.link/dz0mW', 'system'),
                ('BABY/USDT', 'https://mudrex.go.link/BABY', 'system'),
                ('AVAAI/USDT', 'https://mudrex.go.link/AVAAI', 'system'),
                ('STO/USDT', 'https://mudrex.go.link/STO', 'system'),
                ('PIPPIN/USDT', 'https://mudrex.go.link/PIPPIN', 'system'),
                ('ZBCN/USDT', 'https://mudrex.go.link/ZBCN', 'system'),
                ('DOG/USDT', 'https://mudrex.go.link/DOG', 'system'),
                ('NIL/USDT', 'https://mudrex.go.link/NIL', 'system'),
                ('SWARMS/USDT', 'https://mudrex.go.link/SWARMS', 'system'),
                ('ORCA/USDT', 'https://mudrex.go.link/ORCA', 'system'),
                ('1000TURBO/USDT', 'https://mudrex.go.link/TURBO', 'system'),
                ('SYRUP/USDT', 'https://mudrex.go.link/SYRUP', 'system'),
                ('1000CAT/USDT', 'https://mudrex.go.link/CAT', 'system'),
                ('CETUS/USDT', 'https://mudrex.go.link/CETUS', 'system'),
                ('KERNEL/USDT', 'https://mudrex.go.link/KERNEL', 'system'),
                ('THE/USDT', 'https://mudrex.go.link/THE', 'system'),
                ('BIO/USDT', 'https://mudrex.go.link/BIO', 'system'),
                ('FWOG/USDT', 'https://mudrex.go.link/FWOG', 'system'),
                ('USUAL/USDT', 'https://mudrex.go.link/USUAL', 'system'),
                ('BANK/USDT', 'https://mudrex.go.link/BANK', 'system'),
                ('FORM/USDT', 'https://mudrex.go.link/ccbhQ', 'system'),
                ('ACT/USDT', 'https://mudrex.go.link/ACT', 'system'),
                ('HIPPO/USDT', 'https://mudrex.go.link/HIIPPO', 'system'),
                ('PROMPT/USDT', 'https://mudrex.go.link/PROMPT', 'system'),
                ('BEAM/USDT', 'https://mudrex.go.link/BEAM', 'system'),
                ('GIGA/USDT', 'https://mudrex.go.link/GIGA', 'system'),
                ('1000000BABYDOGE/USDT', 'https://mudrex.go.link/BABYDOGE', 'system'),
                ('AKT/USDT', 'https://mudrex.go.link/AKT', 'system'),
                ('TSTBSC/USDT', 'https://mudrex.go.link/TSTBSC', 'system'),
                ('BIGTIME/USDT', 'https://mudrex.go.link/BIGTIME', 'system'),
                ('RAYDIUM/USDT', 'https://mudrex.go.link/RAYDIUM', 'system'),
                ('SKYAI/USDT', 'https://mudrex.go.link/SKYAI', 'system'),
                ('BROCCOLI/USDT', 'https://mudrex.go.link/BROCCOLI', 'system'),
                ('SHELL/USDT', 'https://mudrex.go.link/SHELL', 'system'),
                ('1000000CHEEMS/USDT', 'https://mudrex.go.link/CHEEMS', 'system'),
                ('TUT/USDT', 'https://mudrex.go.link/TUT', 'system'),
                ('1000LUNC/USDT', 'https://mudrex.go.link/LUNC', 'system'),
                ('AWE/USDT', 'https://mudrex.go.link/AWE', 'system'),
                ('B/USDT', 'https://mudrex.go.link/BUSDT', 'system'),
                ('BANANAS31/USDT', 'https://mudrex.go.link/BANANAS31', 'system'),
                ('EPIC/USDT', 'https://mudrex.go.link/8fJvl', 'system'),
                ('F/USDT', 'https://mudrex.go.link/FUSDT', 'system'),
                ('GUN/USDT', 'https://mudrex.go.link/GUN', 'system'),
                ('HEI/USDT', 'https://mudrex.go.link/HEI', 'system'),
                ('LUMIA/USDT', 'https://mudrex.go.link/LUMIA', 'system'),
                ('OL/USDT', 'https://mudrex.go.link/OLUSDT', 'system'),
                ('PEAQ/USDT', 'https://mudrex.go.link/PEAQ', 'system'),
                ('SIREN/USDT', 'https://mudrex.go.link/SIREN', 'system'),
                ('SOON/USDT', 'https://mudrex.go.link/iO7JO', 'system'),
                ('VELODROME/USDT', 'https://mudrex.go.link/VELODROME', 'system'),
                ('ZEUS/USDT', 'https://mudrex.go.link/ZEUS', 'system'),
                ('10000ELON/USDT', 'https://mudrex.go.link/ELON', 'system'),
                ('10000QUBIC/USDT', 'https://mudrex.go.link/QUBIC', 'system'),
                ('1000BTT/USDT', 'https://mudrex.go.link/1000BTT', 'system'),
                ('1000XEC/USDT', 'https://mudrex.go.link/XEC', 'system'),
                ('ACX/USDT', 'https://mudrex.go.link/ACX', 'system'),
                ('ALEO/USDT', 'https://mudrex.go.link/ALEO', 'system'),
                ('ALU/USDT', 'https://mudrex.go.link/ALU', 'system'),
                ('CLANKER/USDT', 'https://mudrex.go.link/CLANKER', 'system'),
                ('ORBS/USDT', 'https://mudrex.go.link/ORBS', 'system'),
                ('USDE/USDT', 'https://mudrex.go.link/USDE', 'system'),
                ('XCH/USDT', 'https://mudrex.go.link/XCHUSDT', 'system'),
                ('BR/USDT', 'https://mudrex.go.link/BRUSDT', 'system'),
                ('CATI/USDT', 'https://mudrex.go.link/CATI', 'system'),
                ('DOOD/USDT', 'https://mudrex.go.link/DOOD', 'system'),
                ('EIGEN/USDT', 'https://mudrex.go.link/EIGEN', 'system'),
                ('EPT/USDT', 'https://mudrex.go.link/EPT', 'system'),
                ('FHE/USDT', 'https://mudrex.go.link/FHE', 'system'),
                ('HIVE/USDT', 'https://mudrex.go.link/HIVE', 'system'),
                ('KAIA/USDT', 'https://mudrex.go.link/KAIA', 'system'),
                ('ME/USDT', 'https://mudrex.go.link/MEUSDT', 'system'),
                ('MLN/USDT', 'https://mudrex.go.link/MLN', 'system'),
                ('MOVE/USDT', 'https://mudrex.go.link/MOVE', 'system'),
                ('NXPC/USDT', 'https://mudrex.go.link/NXPC', 'system'),
                ('OBT/USDT', 'https://mudrex.go.link/OBT', 'system'),
                ('PARTI/USDT', 'https://mudrex.go.link/PARTI', 'system'),
                ('PUNDIX/USDT', 'https://mudrex.go.link/PUNDIXUSDT', 'system'),
                ('RONIN/USDT', 'https://mudrex.go.link/RONIN', 'system'),
                ('VANA/USDT', 'https://mudrex.go.link/VANA', 'system'),
                ('VIC/USDT', 'https://mudrex.go.link/VIC', 'system'),
                ('VVV/USDT', 'https://mudrex.go.link/VVV', 'system'),
                ('WAL/USDT', 'https://mudrex.go.link/WAL', 'system'),
                ('WCT/USDT', 'https://mudrex.go.link/WCT', 'system'),
                ('XAUT/USDT', 'https://mudrex.go.link/kHROS', 'system'),
                ('A/USDT', 'https://mudrex.go.link/ausdt', 'system'),
                ('CUDIS/USDT', 'https://mudrex.go.link/CUDIS', 'system'),
                ('ETHBTC/USDT', 'https://mudrex.go.link/ETHBTC', 'system'),
                ('HOME/USDT', 'https://mudrex.go.link/HOME', 'system'),
                ('HUMA/USDT', 'https://mudrex.go.link/HUMA', 'system'),
                ('LA/USDT', 'https://mudrex.go.link/LAUSDT', 'system'),
                ('PUMPBTC/USDT', 'https://mudrex.go.link/PUMPBTC', 'system'),
                ('RESOLV/USDT', 'https://mudrex.go.link/RESOLV', 'system'),
                ('B2/USDT', 'https://mudrex.go.link/B2USDT', 'system'),
                ('SOPH/USDT', 'https://mudrex.go.link/SOPH', 'system'),
                ('PUMPFUN/USDT', 'https://mudrex.go.link/jFKUX', 'system'),
                ('SOSO/USDT', 'https://mudrex.go.link/bGwua', 'system'),
                ('ICNT/USDT', 'https://mudrex.go.link/8nnku', 'system'),
                ('H/USDT', 'https://mudrex.go.link/3N3rS', 'system'),
                ('SAHARA/USDT', 'https://mudrex.go.link/2neTr', 'system'),
                ('NEWT/USDT', 'https://mudrex.go.link/hH5AK', 'system'),
                ('SPK/USDT', 'https://mudrex.go.link/dP2cL', 'system'),
                ('VELVET/USDT', 'https://mudrex.go.link/cZlZZ', 'system'),
                ('USELESS/USDT', 'https://mudrex.go.link/dXgQf', 'system'),
                ('AIN/USDT', 'https://mudrex.go.link/66wR4', 'system'),
                ('CROSS/USDT', 'https://mudrex.go.link/1ndEh', 'system'),
                ('M/USDT', 'https://mudrex.go.link/aZhIP', 'system'),
                ('C/USDT', 'https://mudrex.go.link/f377s', 'system'),
                ('TAC/USDT', 'https://mudrex.go.link/jg3mL', 'system'),
                ('ES/USDT', 'https://mudrex.go.link/b00VX', 'system'),
                ('ERA/USDT', 'https://mudrex.go.link/ktfiK', 'system'),
                ('TA/USDT', 'https://mudrex.go.link/4bxoG', 'system'),
                ('ASP/USDT', 'https://mudrex.go.link/8aBA2', 'system'),
                ('DOLO/USDT', 'https://mudrex.go.link/iVGig', 'system'),
                ('1000TAG/USDT', 'https://mudrex.go.link/gVIRT', 'system'),
                ('ESPORTS/USDT', 'https://mudrex.go.link/J5usQ', 'system'),
                ('TREE/USDT', 'https://mudrex.go.link/8J2Yu', 'system'),
                ('A2Z/USDT', 'https://mudrex.go.link/fUaVq', 'system'),
                ('DIA/USDT', 'https://mudrex.go.link/22gQZ', 'system'),
                ('MYX/USDT', 'https://mudrex.go.link/gm1fQ', 'system'),
                ('TOWNS/USDT', 'https://mudrex.go.link/hbc7F', 'system'),
                ('PROVE/USDT', 'https://mudrex.go.link/aWDI9', 'system'),
                ('IN/USDT', 'https://mudrex.go.link/dQsmN', 'system'),
                ('YALA/USDT', 'https://mudrex.go.link/6GvTL', 'system'),
                ('ASR/USDT', 'https://mudrex.go.link/bBezC', 'system'),
                ('XNY/USDT', 'https://mudrex.go.link/bhJsU', 'system'),
                ('AIO/USDT', 'https://mudrex.go.link/KIdK3', 'system'),
                ('ALPINE/USDT', 'https://mudrex.go.link/9TYzA', 'system'),
                ('NAORIS/USDT', 'https://mudrex.go.link/gtWqJ', 'system'),
                ('SKY/USDT', 'https://mudrex.go.link/6nyvt', 'system'),
                ('YZY/USDT', 'https://mudrex.go.link/KMna6', 'system'),
                ('SAPIEN/USDT', 'https://mudrex.go.link/7N7pS', 'system'),
                ('BTR/USDT', 'https://mudrex.go.link/bcLHJ', 'system'),
                ('BSU/USDT', 'https://mudrex.go.link/5Bi3h', 'system'),
                ('WLFI/USDT', 'https://mudrex.go.link/3KpRP', 'system'),
                ('PTB/USDT', 'https://mudrex.go.link/aNKHf', 'system'),
                ('ARIA/USDT', 'https://mudrex.go.link/8UX32', 'system'),
                ('SOMI/USDT', 'https://mudrex.go.link/3TzGw', 'system'),
                ('MITO/USDT', 'https://mudrex.go.link/aAOcy', 'system'),
                ('CAMP/USDT', 'https://mudrex.go.link/2UCG3', 'system'),
                ('POWER/USDT', 'https://mudrex.go.link/POWER', 'system'),
                ('MAGMA/USDT', 'https://mudrex.go.link/MAGMA', 'system'),
                ('BREV/USDT', 'https://mudrex.go.link/BREV', 'system'),
            ]

            cur.executemany(
                "INSERT INTO active_pairs (symbol, adjust_link, added_by) VALUES (%s, %s, %s)",
                initial_pairs
            )
            conn.commit()
            logger.info(f"✅ Seeded {len(initial_pairs)} trading pairs with Adjust links")
            return len(initial_pairs)
    except Exception as e:
        conn.rollback()
        logger.error(f"Failed to seed pairs: {e}")
        return 0
    finally:
        conn.close()


# ==========================================
# ADJUST LINK CACHE FUNCTIONS (for AI mode)
# ==========================================

def get_cached_adjust_link(bybit_symbol: str) -> Optional[str]:
    """
    Get cached Adjust link for a Bybit symbol

    Returns:
        - URL string if found
        - Empty string '' if explicitly marked as unavailable
        - None if not cached yet
    """
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT adjust_link FROM adjust_link_cache
                WHERE bybit_symbol = %s
            """, (bybit_symbol,))

            result = cur.fetchone()
            if result is not None:
                return result[0]  # Returns URL or empty string
            return None  # Not cached

    except Exception as e:
        logger.error(f"Error getting cached link: {e}")
        return None
    finally:
        conn.close()


def cache_adjust_link(bybit_symbol: str, adjust_link: str, found_by: str = 'ai'):
    """
    Cache Adjust link for future use

    Args:
        bybit_symbol: Bybit symbol (e.g., "1000SHIB/USDT")
        adjust_link: Adjust URL or empty string for unavailable
        found_by: Source of the link ('ai', 'manual', 'seed')
    """
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO adjust_link_cache (bybit_symbol, adjust_link, found_by, updated_at)
                VALUES (%s, %s, %s, NOW())
                ON CONFLICT (bybit_symbol)
                DO UPDATE SET adjust_link = EXCLUDED.adjust_link,
                              found_by = EXCLUDED.found_by,
                              updated_at = NOW()
            """, (bybit_symbol, adjust_link, found_by))
            conn.commit()

            status = "unavailable" if adjust_link == '' else "cached"
            logger.debug(f"Cached: {bybit_symbol} -> {status}")

    except Exception as e:
        conn.rollback()
        logger.error(f"Error caching link: {e}")
    finally:
        conn.close()


def get_all_known_adjust_links() -> Dict:
    """
    Load all known Adjust links for AI context
    Returns: {symbol: adjust_link}
    """
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            # Get from cache table
            cur.execute("""
                SELECT bybit_symbol, adjust_link
                FROM adjust_link_cache
                WHERE adjust_link != ''
            """)
            cache_results = cur.fetchall()

            # Also get from active_pairs table
            cur.execute("""
                SELECT symbol, adjust_link
                FROM active_pairs
                WHERE status = 'active' AND adjust_link IS NOT NULL AND adjust_link != ''
            """)
            pairs_results = cur.fetchall()

            # Combine both sources
            links = {}
            for row in cache_results:
                links[row[0]] = row[1]
            for row in pairs_results:
                if row[0] not in links:
                    links[row[0]] = row[1]

            return links

    except Exception as e:
        logger.error(f"Error loading known links: {e}")
        return {}
    finally:
        conn.close()


def save_session_start_price(symbol: str, price: float):
    """Save session start price for a new pair (for native Bybit mode)"""
    conn = get_connection()
    try:
        today = date.today()

        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO session_prices (symbol, session_date, start_price)
                VALUES (%s, %s, %s)
                ON CONFLICT (symbol, session_date)
                DO NOTHING
            """, (symbol, today, price))
            conn.commit()

    except Exception as e:
        conn.rollback()
        logger.error(f"Error saving session price: {e}")
    finally:
        conn.close()


def get_session_start_price_native(symbol: str) -> Optional[float]:
    """Get session start price for native Bybit mode"""
    conn = get_connection()
    try:
        today = date.today()

        with conn.cursor() as cur:
            cur.execute("""
                SELECT start_price FROM session_prices
                WHERE symbol = %s AND session_date = %s
            """, (symbol, today))

            result = cur.fetchone()
            return float(result[0]) if result else None

    except Exception as e:
        logger.error(f"Error getting session start price: {e}")
        return None
    finally:
        conn.close()


def clear_session_prices():
    """Clear all session prices (for daily reset)"""
    conn = get_connection()
    try:
        yesterday = date.today() - timedelta(days=1)

        with conn.cursor() as cur:
            cur.execute("""
                DELETE FROM session_prices
                WHERE session_date < %s
            """, (yesterday,))
            conn.commit()
            logger.info("Cleared old session prices")

    except Exception as e:
        conn.rollback()
        logger.error(f"Error clearing session prices: {e}")
    finally:
        conn.close()


def initialize_database():
    """Initialize database with schema (auto-creates tables if not exist)"""
    schema = """
    -- Active pairs with Adjust links
    CREATE TABLE IF NOT EXISTS active_pairs (
        id SERIAL PRIMARY KEY,
        symbol VARCHAR(20) UNIQUE NOT NULL,
        adjust_link TEXT NOT NULL,
        status VARCHAR(20) DEFAULT 'active',
        added_by VARCHAR(50),
        added_at TIMESTAMP DEFAULT NOW(),
        last_scanned TIMESTAMP,
        CONSTRAINT valid_symbol CHECK (symbol ~ '^[A-Z0-9]+/USDT$')
    );

    -- Price snapshots (24h history + session start price)
    CREATE TABLE IF NOT EXISTS price_snapshots (
        id SERIAL PRIMARY KEY,
        symbol VARCHAR(20) NOT NULL,
        price DECIMAL(20, 8) NOT NULL,
        volume_24h DECIMAL(20, 2),
        session_start_price DECIMAL(20, 8),
        timestamp TIMESTAMP DEFAULT NOW(),
        source VARCHAR(10) NOT NULL,
        FOREIGN KEY (symbol) REFERENCES active_pairs(symbol) ON DELETE CASCADE
    );

    -- Alert history (track fired alerts per session)
    CREATE TABLE IF NOT EXISTS alert_history (
        id SERIAL PRIMARY KEY,
        symbol VARCHAR(20) NOT NULL,
        threshold_percent DECIMAL NOT NULL,
        alert_type VARCHAR(10) NOT NULL,
        trigger_price DECIMAL(20, 8) NOT NULL,
        session_start_price DECIMAL(20, 8) NOT NULL,
        actual_change_percent DECIMAL NOT NULL,
        volume_24h DECIMAL(20, 2),
        telegram_message_id BIGINT,
        session_date DATE NOT NULL,
        created_at TIMESTAMP DEFAULT NOW(),
        FOREIGN KEY (symbol) REFERENCES active_pairs(symbol) ON DELETE CASCADE
    );

    -- Bot configuration
    CREATE TABLE IF NOT EXISTS bot_config (
        key VARCHAR(50) PRIMARY KEY,
        value TEXT NOT NULL,
        updated_at TIMESTAMP DEFAULT NOW(),
        updated_by VARCHAR(50)
    );

    -- Scanner logs (for monitoring)
    CREATE TABLE IF NOT EXISTS scanner_logs (
        id SERIAL PRIMARY KEY,
        scan_cycle INT NOT NULL,
        pairs_scanned INT,
        alerts_triggered INT,
        errors INT,
        duration_seconds DECIMAL,
        timestamp TIMESTAMP DEFAULT NOW()
    );

    -- Adjust link cache (for AI-discovered links)
    CREATE TABLE IF NOT EXISTS adjust_link_cache (
        bybit_symbol VARCHAR(30) PRIMARY KEY,
        adjust_link TEXT NOT NULL DEFAULT '',
        updated_at TIMESTAMP DEFAULT NOW(),
        found_by VARCHAR(20) DEFAULT 'ai'
    );

    -- Session start prices (for native Bybit mode)
    CREATE TABLE IF NOT EXISTS session_prices (
        symbol VARCHAR(30) NOT NULL,
        session_date DATE NOT NULL,
        start_price DECIMAL(20, 8) NOT NULL,
        created_at TIMESTAMP DEFAULT NOW(),
        PRIMARY KEY (symbol, session_date)
    );

    -- Default config values
    INSERT INTO bot_config (key, value) VALUES
        ('cooldown_minutes', '0'),
        ('min_volume_usd', '5000000'),
        ('scanner_status', 'running'),
        ('native_bybit_mode', 'false'),
        ('ai_mode_enabled', 'false')
    ON CONFLICT (key) DO NOTHING;

    -- Indexes for performance
    CREATE INDEX IF NOT EXISTS idx_price_snapshots_symbol_time ON price_snapshots(symbol, timestamp DESC);
    CREATE INDEX IF NOT EXISTS idx_alert_history_session ON alert_history(symbol, session_date, threshold_percent);
    CREATE INDEX IF NOT EXISTS idx_active_pairs_status ON active_pairs(status);

    -- Cleanup function
    CREATE OR REPLACE FUNCTION cleanup_old_data() RETURNS void AS $$
    BEGIN
        DELETE FROM price_snapshots WHERE timestamp < NOW() - INTERVAL '25 hours';
        DELETE FROM scanner_logs WHERE timestamp < NOW() - INTERVAL '30 days';
    END;
    $$ LANGUAGE plpgsql;
    """

    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(schema)
            conn.commit()
            logger.info("✅ Database schema initialized")
    except Exception as e:
        conn.rollback()
        logger.error(f"Failed to initialize database: {e}")
        raise
    finally:
        conn.close()
