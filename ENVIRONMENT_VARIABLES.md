# Environment Variables Configuration

## Railway Environment Variables

This document explains the environment variables used by the Price Alert Bot.

### Required Variables (MUST be set):

| Variable | Description | Example |
|----------|-------------|---------|
| `TELEGRAM_BOT_TOKEN` | Your Telegram bot token from @BotFather | `7123456789:AAH...` |
| `TELEGRAM_GROUP_ID` | Your Telegram group/channel ID | `-1002123456789` |
| `PRICE_ALERTS_TOPIC_ID` | Topic ID for alerts in group | `123` |
| `DATABASE_URL` | PostgreSQL database URL (Railway provides this) | `postgresql://...` |
| `ADMIN_USER_IDS` | Comma-separated list of admin Telegram user IDs | `123456789,987654321` |
| `GEMINI_API_KEY` | Gemini API key for AI link discovery | `AIza...` |

### Optional Variables (Initial Defaults Only):

| Variable | Description | Default | Runtime Command |
|----------|-------------|---------|----------------|
| `SCAN_INTERVAL` | Scan interval in seconds | `30` | `/interval 30s` |
| `MIN_VOLUME_USD` | Minimum 24h volume filter (USD) | `5000000` | `/volume 5M` |
| `LOG_LEVEL` | Logging level | `INFO` | N/A |

## Important Notes:

### 🔄 Dynamic Configuration (Recommended)

**Use commands to change settings at runtime:**

```bash
# Change scan interval (takes effect after restart)
/interval 30s
/interval 1m

# Change volume filter (takes effect immediately)
/volume 5M
/volume 10M
/volume reset

# View current settings
/interval
/volume
/status
```

### ⚠️ Environment Variables vs Commands

**Environment Variables:**
- Used as **initial defaults only** on first startup
- If you change an env var, you must **restart the bot** for it to take effect
- Database values (set by commands) **override** env vars after first startup

**Runtime Commands:**
- Update database configuration
- Persist across restarts
- More convenient than changing env vars

### Example Flow:

1. **First Deployment:**
   ```
   ENV: SCAN_INTERVAL=30, MIN_VOLUME_USD=5000000
   Bot starts → Uses 30s interval and $5M volume
   ```

2. **User runs `/interval 60s`:**
   ```
   Database updated: scan_interval_seconds=60
   Bot requires restart to apply
   ```

3. **Bot Restarts:**
   ```
   Bot reads database: scan_interval_seconds=60
   Uses 60s interval (ignores env var)
   ```

4. **User runs `/interval reset`:**
   ```
   Database cleared for scan_interval
   Bot falls back to env var: SCAN_INTERVAL=30
   ```

### Best Practices:

✅ **DO:**
- Set env vars to sensible defaults for your use case
- Use commands (`/interval`, `/volume`) for runtime changes
- Use `/status` to verify current settings

❌ **DON'T:**
- Change env vars expecting immediate effect (requires restart)
- Remove env vars unless you want hardcoded defaults
- Mix env var changes with database commands (confusing)

### Summary:

**Keep the environment variables** - they serve as convenient defaults and fallbacks. The system is designed to work this way:

```
Startup: ENV_VAR → Database (if exists) → Runtime
         ↑ Default     ↑ Override          ↑ Active value
```

Use commands for runtime configuration, env vars for deployment defaults.

---
**Last Updated:** 2026-01-28
**Recommendation:** Keep both `SCAN_INTERVAL` and `MIN_VOLUME_USD` env vars as documented initial defaults.
