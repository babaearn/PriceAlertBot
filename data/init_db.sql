-- ================================================================
-- TELEGRAM PRICE ALERT BOT - DATABASE SCHEMA
-- ================================================================

-- Active pairs with Adjust links (478 pairs initially)
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

-- Comment on tables
COMMENT ON TABLE active_pairs IS 'Trading pairs with Adjust links (478 pairs)';
COMMENT ON TABLE price_snapshots IS 'Historical price data with session start prices';
COMMENT ON TABLE alert_history IS 'Fired alerts to prevent duplicates per session';
COMMENT ON TABLE bot_config IS 'Bot configuration key-value store';
COMMENT ON TABLE scanner_logs IS 'Scanner performance monitoring';
