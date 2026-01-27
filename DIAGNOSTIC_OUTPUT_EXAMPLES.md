# 🔍 Diagnostic Output Examples

## What to Look For in Railway Logs

When you deploy the bot, you'll see comprehensive diagnostics that will **immediately identify the problem**.

---

## ✅ Scenario 1: FILE FOUND (Success)

```bash
2026-01-27 11:06:00 | INFO | __main__ |
======================================================================
🔍 STARTUP DIAGNOSTICS - ADJUST LINKS VERIFICATION
======================================================================

2026-01-27 11:06:00 | INFO | bot.services.adjust_links | 🚀 Initializing adjust_links module...
2026-01-27 11:06:00 | INFO | bot.services.adjust_links | ============================================================
2026-01-27 11:06:00 | INFO | bot.services.adjust_links | 🔍 VERIFYING ADJUST LINKS JSON FILE
2026-01-27 11:06:00 | INFO | bot.services.adjust_links | ============================================================
2026-01-27 11:06:00 | INFO | bot.services.adjust_links | 📁 Checking 5 possible file locations:
2026-01-27 11:06:00 | INFO | bot.services.adjust_links |
2026-01-27 11:06:00 | INFO | bot.services.adjust_links | 1. /app/bot/services/../../data/adjust_links.json
2026-01-27 11:06:00 | INFO | bot.services.adjust_links |    Absolute: /app/data/adjust_links.json
2026-01-27 11:06:00 | INFO | bot.services.adjust_links |    Exists: ✅ YES
2026-01-27 11:06:00 | INFO | bot.services.adjust_links |    Is file: ✅ YES
2026-01-27 11:06:00 | INFO | bot.services.adjust_links |    Size: 1654 bytes
2026-01-27 11:06:00 | INFO | bot.services.adjust_links |    Content length: 1654 chars
2026-01-27 11:06:00 | INFO | bot.services.adjust_links |    JSON valid: ✅ YES
2026-01-27 11:06:00 | INFO | bot.services.adjust_links |    Entries: 21 adjust links
2026-01-27 11:06:00 | INFO | bot.services.adjust_links |    Sample entries:
2026-01-27 11:06:00 | INFO | bot.services.adjust_links |       - BTC/USDT: https://mudrex.go.link/1Yogo
2026-01-27 11:06:00 | INFO | bot.services.adjust_links |       - ETH/USDT: https://mudrex.go.link/kmYNX
2026-01-27 11:06:00 | INFO | bot.services.adjust_links |       - BNB/USDT: https://mudrex.go.link/3G8Mh
2026-01-27 11:06:00 | INFO | bot.services.adjust_links | ============================================================
2026-01-27 11:06:00 | INFO | bot.services.adjust_links | 📥 LOADING ADJUST LINKS
2026-01-27 11:06:00 | INFO | bot.services.adjust_links | ============================================================
2026-01-27 11:06:00 | INFO | bot.services.adjust_links | 📂 Loading from: /app/data/adjust_links.json
2026-01-27 11:06:00 | INFO | bot.services.adjust_links | ✅ JSON parsed: 21 entries
2026-01-27 11:06:00 | INFO | bot.services.adjust_links | ✅ Loaded 21 adjust links
2026-01-27 11:06:00 | INFO | bot.services.adjust_links | ✅ Cache size: 42 entries (including normalized)
2026-01-27 11:06:00 | INFO | bot.services.adjust_links |
2026-01-27 11:06:00 | INFO | bot.services.adjust_links | 📊 Sample adjust links:
2026-01-27 11:06:00 | INFO | bot.services.adjust_links |    1. BTC/USDT: https://mudrex.go.link/1Yogo
2026-01-27 11:06:00 | INFO | bot.services.adjust_links |    2. BTCUSDT: https://mudrex.go.link/1Yogo
2026-01-27 11:06:00 | INFO | bot.services.adjust_links |    3. ETH/USDT: https://mudrex.go.link/kmYNX
2026-01-27 11:06:00 | INFO | bot.services.adjust_links |    4. ETHUSDT: https://mudrex.go.link/kmYNX
2026-01-27 11:06:00 | INFO | bot.services.adjust_links |    5. BNB/USDT: https://mudrex.go.link/3G8Mh
2026-01-27 11:06:00 | INFO | bot.services.adjust_links | ============================================================
2026-01-27 11:06:00 | INFO | bot.services.adjust_links |
2026-01-27 11:06:00 | INFO | bot.services.adjust_links | ✅ Adjust links module initialized successfully
2026-01-27 11:06:00 | INFO | __main__ |
2026-01-27 11:06:00 | INFO | __main__ | 📊 Adjust Links Cache Statistics:
2026-01-27 11:06:00 | INFO | __main__ |    Total entries: 42
2026-01-27 11:06:00 | INFO | __main__ |    Cache loaded: ✅ YES
2026-01-27 11:06:00 | INFO | __main__ |    Sample symbols: BTC/USDT, BTCUSDT, ETH/USDT, ETHUSDT, BNB/USDT
2026-01-27 11:06:00 | INFO | __main__ |
2026-01-27 11:06:00 | INFO | __main__ | ✅ Adjust links module loaded successfully
2026-01-27 11:06:00 | INFO | __main__ | ======================================================================
```

**Result:** ✅ File found! Bot will work perfectly, alerts will include adjust links.

---

## ❌ Scenario 2: FILE NOT FOUND (Problem Identified)

```bash
2026-01-27 11:06:00 | INFO | __main__ |
======================================================================
🔍 STARTUP DIAGNOSTICS - ADJUST LINKS VERIFICATION
======================================================================

2026-01-27 11:06:00 | INFO | bot.services.adjust_links | 🚀 Initializing adjust_links module...
2026-01-27 11:06:00 | INFO | bot.services.adjust_links | ============================================================
2026-01-27 11:06:00 | INFO | bot.services.adjust_links | 🔍 VERIFYING ADJUST LINKS JSON FILE
2026-01-27 11:06:00 | INFO | bot.services.adjust_links | ============================================================
2026-01-27 11:06:00 | INFO | bot.services.adjust_links | 📁 Checking 5 possible file locations:
2026-01-27 11:06:00 | INFO | bot.services.adjust_links |
2026-01-27 11:06:00 | INFO | bot.services.adjust_links | 1. /app/bot/services/../../data/adjust_links.json
2026-01-27 11:06:00 | INFO | bot.services.adjust_links |    Absolute: /app/data/adjust_links.json
2026-01-27 11:06:00 | INFO | bot.services.adjust_links |    Exists: ❌ NO
2026-01-27 11:06:00 | INFO | bot.services.adjust_links |
2026-01-27 11:06:00 | INFO | bot.services.adjust_links | 2. /app/data/adjust_links.json
2026-01-27 11:06:00 | INFO | bot.services.adjust_links |    Absolute: /app/data/adjust_links.json
2026-01-27 11:06:00 | INFO | bot.services.adjust_links |    Exists: ❌ NO
2026-01-27 11:06:00 | INFO | bot.services.adjust_links |
2026-01-27 11:06:00 | INFO | bot.services.adjust_links | 3. ./data/adjust_links.json
2026-01-27 11:06:00 | INFO | bot.services.adjust_links |    Absolute: /app/data/adjust_links.json
2026-01-27 11:06:00 | INFO | bot.services.adjust_links |    Exists: ❌ NO
2026-01-27 11:06:00 | INFO | bot.services.adjust_links |
2026-01-27 11:06:00 | INFO | bot.services.adjust_links | 4. data/adjust_links.json
2026-01-27 11:06:00 | INFO | bot.services.adjust_links |    Absolute: /app/data/adjust_links.json
2026-01-27 11:06:00 | INFO | bot.services.adjust_links |    Exists: ❌ NO
2026-01-27 11:06:00 | INFO | bot.services.adjust_links |
2026-01-27 11:06:00 | INFO | bot.services.adjust_links | 5. /app/adjust_links.json
2026-01-27 11:06:00 | INFO | bot.services.adjust_links |    Absolute: /app/adjust_links.json
2026-01-27 11:06:00 | INFO | bot.services.adjust_links |    Exists: ❌ NO
2026-01-27 11:06:00 | ERROR | bot.services.adjust_links |
2026-01-27 11:06:00 | ERROR | bot.services.adjust_links | ============================================================
2026-01-27 11:06:00 | ERROR | bot.services.adjust_links | ❌ ADJUST LINKS FILE NOT FOUND IN ANY LOCATION
2026-01-27 11:06:00 | ERROR | bot.services.adjust_links | ============================================================
2026-01-27 11:06:00 | INFO | bot.services.adjust_links |
2026-01-27 11:06:00 | INFO | bot.services.adjust_links | 📂 Current working directory: /app
2026-01-27 11:06:00 | INFO | bot.services.adjust_links | 📂 Directory contents:
2026-01-27 11:06:00 | INFO | bot.services.adjust_links |    📁 DIR : bot
2026-01-27 11:06:00 | INFO | bot.services.adjust_links |    📄 FILE: Dockerfile
2026-01-27 11:06:00 | INFO | bot.services.adjust_links |    📄 FILE: README.md
2026-01-27 11:06:00 | INFO | bot.services.adjust_links |    📄 FILE: requirements.txt
2026-01-27 11:06:00 | INFO | bot.services.adjust_links |
2026-01-27 11:06:00 | INFO | bot.services.adjust_links | 📂 Checking 'data/' directory:
2026-01-27 11:06:00 | ERROR | bot.services.adjust_links |    ❌ data/ directory does NOT exist
2026-01-27 11:06:00 | INFO | bot.services.adjust_links |
2026-01-27 11:06:00 | INFO | bot.services.adjust_links | ============================================================
2026-01-27 11:06:00 | INFO | bot.services.adjust_links | 💡 SOLUTIONS:
2026-01-27 11:06:00 | INFO | bot.services.adjust_links | ============================================================
2026-01-27 11:06:00 | INFO | bot.services.adjust_links | 1. Ensure data/adjust_links.json is in your repository
2026-01-27 11:06:00 | INFO | bot.services.adjust_links | 2. Check your Dockerfile COPY commands
2026-01-27 11:06:00 | INFO | bot.services.adjust_links | 3. Verify file is not in .dockerignore
2026-01-27 11:06:00 | INFO | bot.services.adjust_links | 4. Use absolute path in Docker: COPY data/ /app/data/
2026-01-27 11:06:00 | INFO | bot.services.adjust_links | ============================================================
2026-01-27 11:06:00 | ERROR | bot.services.adjust_links |
2026-01-27 11:06:00 | ERROR | bot.services.adjust_links | ❌ Cannot load adjust links - file not found
2026-01-27 11:06:00 | ERROR | bot.services.adjust_links | ⚠️  Bot will continue but NO ALERTS will have adjust links!
2026-01-27 11:06:00 | ERROR | __main__ |
2026-01-27 11:06:00 | ERROR | __main__ | ❌ WARNING: Adjust links cache is EMPTY!
2026-01-27 11:06:00 | ERROR | __main__ |    Alerts will NOT include adjust deeplinks!
```

**Result:** ❌ File missing! This tells you **exactly** what's wrong:
- data/ directory doesn't exist in the container
- Need to check Dockerfile COPY commands
- Need to verify git tracking of file

---

## 🔍 What Happened: Most Common Issue

### **Problem: File Not Copied to Docker Image**

**Root Cause:**
```dockerfile
# ❌ WRONG Dockerfile (excludes data/)
COPY bot/ /app/bot/
COPY requirements.txt /app/
# data/ directory never copied!
```

**Solution:**
```dockerfile
# ✅ CORRECT Dockerfile
COPY . .
# Copies everything including data/
```

---

## 🛠️ Docker Build Diagnostics

The Dockerfile also runs diagnostics during **build time**:

```bash
# Railway Build Logs
[build] Step 5/8 : RUN echo "...
[build] ============================================================
[build] 🔍 VERIFYING ADJUST LINKS FILE IN DOCKER IMAGE
[build] ============================================================
[build] total 48
[build] drwxr-xr-x  1 root root  4096 Jan 27 11:05 .
[build] drwxr-xr-x  1 root root  4096 Jan 27 11:05 ..
[build] drwxr-xr-x  2 root root  4096 Jan 27 11:05 bot
[build] drwxr-xr-x  2 root root  4096 Jan 27 11:05 data  ← ✅ data/ exists!
[build] -rw-r--r--  1 root root  1234 Jan 27 11:05 requirements.txt
[build] ------------------------------------------------------------
[build] total 16
[build] drwxr-xr-x  2 root root  4096 Jan 27 11:05 .
[build] drwxr-xr-x  1 root root  4096 Jan 27 11:05 ..
[build] -rw-r--r--  1 root root  1654 Jan 27 11:05 adjust_links.json  ← ✅ File exists!
[build] -rw-r--r--  1 root root  3232 Jan 27 11:05 init_db.sql
[build] ------------------------------------------------------------
[build] ✅ adjust_links.json FOUND
[build] 📄 File size: 1654 bytes
[build] 📋 First 3 lines:
[build] [
[build]   {
[build]     "symbol": "BTC/USDT",
[build] ============================================================
```

**This tells you the file WAS copied successfully during build!**

---

## 📊 Quick Diagnosis Checklist

Use this checklist when reading logs:

### ✅ Success Indicators:
```
✅ adjust_links.json FOUND              (in build logs)
✅ Loaded 21 adjust links                (in startup logs)
✅ Cache size: 42 entries                (in startup logs)
✅ Adjust links module initialized       (in startup logs)
```

### ❌ Failure Indicators:
```
❌ data/ directory does NOT exist        (file not copied)
❌ adjust_links.json NOT FOUND           (file missing)
❌ Adjust links cache is EMPTY           (file empty/invalid)
⚠️  Bot will continue but NO ALERTS      (warning)
```

---

## 🎯 Action Items Based on Logs

### If you see: `❌ data/ directory does NOT exist`
**Problem:** Dockerfile not copying data/ folder
**Fix:** Change Dockerfile to `COPY . .`

### If you see: `❌ adjust_links.json NOT FOUND`
**Problem:** File not in repository or .dockerignore excludes it
**Fix:**
1. Verify: `git ls-files data/adjust_links.json`
2. Check: `.dockerignore` doesn't have `data/` or `*.json`

### If you see: `❌ Adjust links cache is EMPTY`
**Problem:** File exists but empty or invalid JSON
**Fix:** Check file contents, ensure valid JSON syntax

### If you see: `✅ Loaded 0 adjust links`
**Problem:** JSON file has wrong structure
**Fix:** Verify JSON has `{"symbol": "...", "adjust_link": "..."}` format

---

## 🚀 Next Steps After Deployment

1. **Check Railway logs immediately** after deployment
2. **Look for the diagnostic section** (first 50 lines)
3. **Identify if file was found** (✅ or ❌)
4. **Follow solutions** provided in logs
5. **Redeploy** after fixing

**With these diagnostics, you'll know exactly what's wrong within 10 seconds of deployment!** 🎯
