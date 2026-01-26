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
        conn = psycopg2.connect(config.DATABASE_URL)
        return conn
    except Exception as e:
        logger.error(f"Database connection failed: {e}")
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

    -- Default config values
    INSERT INTO bot_config (key, value) VALUES
        ('cooldown_minutes', '0'),
        ('min_volume_usd', '5000000'),
        ('scanner_status', 'running')
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
