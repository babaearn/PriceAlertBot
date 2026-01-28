# Railway Setup Guide - Quick Reference

## Environment Variables Configuration

### ✅ Required Variables (Must Set These):

Copy these into Railway Variables tab:

```bash
# Telegram Configuration (REQUIRED)
TELEGRAM_BOT_TOKEN=your_bot_token_here
TELEGRAM_GROUP_ID=-1002123456789
PRICE_ALERTS_TOPIC_ID=123
ADMIN_USER_IDS=123456789,987654321

# Database (Railway provides automatically)
DATABASE_URL=postgresql://...

# AI Features (REQUIRED for adjust links)
GEMINI_API_KEY=your_gemini_api_key_here
```

### 🔧 Optional Variables (Initial Defaults):

**You can set these, but they're NOT required:**

```bash
# Scanning Configuration (Optional - can change via commands)
SCAN_INTERVAL=30              # Default: 30 seconds (use /interval to change)
MIN_VOLUME_USD=5000000        # Default: $5M (use /volume to change)

# Logging (Optional)
LOG_LEVEL=INFO                # Default: INFO
```

## What Should You Do?

### Option 1: Keep Optional Variables (Recommended)
**Best for:** Setting sensible defaults for your deployment

✅ Keep `SCAN_INTERVAL=30` in Railway
✅ Keep `MIN_VOLUME_USD=5000000` in Railway
✅ Use `/interval` and `/volume` commands to change at runtime
✅ Changes persist in database across restarts

**Pros:**
- Clean first deployment with good defaults
- Easy to reset to defaults with `/interval reset` or `/volume reset`
- Flexible for different deployment environments

### Option 2: Remove Optional Variables
**Best for:** Forcing all configuration through Telegram commands

❌ Remove `SCAN_INTERVAL` from Railway
❌ Remove `MIN_VOLUME_USD` from Railway
✅ Bot uses hardcoded defaults (30s, $5M)
✅ Must use commands to change settings

**Pros:**
- Simpler - fewer variables to manage
- Single source of truth (database only)

**Cons:**
- Every new deployment needs manual setup via commands
- Can't easily have different defaults for dev/prod

## My Recommendation:

**🎯 Keep the optional variables but understand they're just defaults:**

```
Railway Variables:
┌─────────────────────────────────────────┐
│ ✅ REQUIRED (Must set):                │
│   • TELEGRAM_BOT_TOKEN                  │
│   • TELEGRAM_GROUP_ID                   │
│   • PRICE_ALERTS_TOPIC_ID               │
│   • ADMIN_USER_IDS                      │
│   • GEMINI_API_KEY                      │
│   • DATABASE_URL (auto-provided)        │
│                                          │
│ 🔧 OPTIONAL (Initial defaults):        │
│   • SCAN_INTERVAL=30                    │
│   • MIN_VOLUME_USD=5000000              │
│                                          │
│ 💡 TIP: Use /interval and /volume      │
│    commands to change at runtime!       │
└─────────────────────────────────────────┘
```

## Runtime Configuration (Preferred):

Instead of changing env vars, use these commands:

```bash
# Change scan interval
/interval 30s    # 30 seconds
/interval 1m     # 1 minute
/interval 2m     # 2 minutes
/interval reset  # Reset to env var default

# Change volume filter
/volume 5M       # $5 million
/volume 10M      # $10 million
/volume 1B       # $1 billion
/volume reset    # Reset to env var default

# View current settings
/interval        # Show current interval
/volume          # Show current volume filter
/status          # Full status info
/show            # Show filtered pairs count
```

## Visual Guide:

```
Startup Flow:
═════════════

1️⃣ Bot Starts
   ↓
   Reads ENV: SCAN_INTERVAL=30
   ↓
   Checks Database: scan_interval_seconds
   ↓
   Database empty? → Use 30s from env var ✅
   Database has value? → Use database value ✅

2️⃣ User runs: /interval 60s
   ↓
   Database updated: scan_interval_seconds=60
   ↓
   Message: "⚠️ Restart bot to apply"

3️⃣ Bot Restarts
   ↓
   Reads ENV: SCAN_INTERVAL=30
   ↓
   Checks Database: scan_interval_seconds=60 ✅
   ↓
   Uses 60s (database wins!)

4️⃣ User runs: /interval reset
   ↓
   Database cleared
   ↓
   Falls back to env var: 30s ✅
```

## Quick Decision Matrix:

| Your Goal | Action | Reason |
|-----------|--------|--------|
| Simple setup, good defaults | ✅ Keep both variables | Easy first deployment |
| Minimize Railway variables | ❌ Remove both variables | Fewer things to manage |
| Different defaults per environment | ✅ Keep both variables | Dev vs Prod flexibility |
| Runtime-only configuration | ❌ Remove both variables | Forces command usage |

## Summary:

**The system is designed to work EITHER way:**

- **With env vars:** Convenient defaults that can be overridden
- **Without env vars:** Hardcoded defaults (30s, $5M) that can be overridden

**My recommendation:** Keep them for convenience, but know you can always change via commands.

---
**Last Updated:** 2026-01-28
