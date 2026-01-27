# 🔍 Adjust Links Troubleshooting Guide

## Overview

This bot uses `data/adjust_links.json` to provide Mudrex app deeplinks in price alerts. If this file is missing or improperly loaded, alerts will NOT include the deeplinks.

---

## 🚨 Common Symptoms

### **Symptom 1: No Adjust Links in Alerts**
**Alert message shows but no "View Chart" button**

**Diagnosis:**
```bash
# Check bot logs for:
❌ No adjust link found for: BTC/USDT
⚠️  Skipping alert - no adjust link
```

### **Symptom 2: File Not Found Error**
**Bot logs show:**
```bash
❌ ADJUST LINKS FILE NOT FOUND IN ANY LOCATION
```

### **Symptom 3: Empty Cache**
**Bot logs show:**
```bash
✅ Loaded 0 adjust links
❌ WARNING: Adjust links cache is EMPTY!
```

---

## 🔍 Diagnostic Logs

When the bot starts, you'll see comprehensive diagnostics:

```bash
============================================================
🔍 VERIFYING ADJUST LINKS JSON FILE
============================================================
📁 Checking 5 possible file locations:

1. /app/bot/services/../../data/adjust_links.json
   Absolute: /app/data/adjust_links.json
   Exists: ✅ YES
   Is file: ✅ YES
   Size: 1234 bytes
   JSON valid: ✅ YES
   Entries: 21 adjust links
   Sample entries:
      - BTC/USDT: https://mudrex.go.link/1Yogo
      - ETH/USDT: https://mudrex.go.link/kmYNX
```

---

## ✅ Quick Fixes

### **Fix 1: Verify File Exists in Repository**

```bash
# In your local repository
ls -la data/adjust_links.json

# Should show:
-rw-r--r-- 1 user user 1234 Jan 22 10:00 data/adjust_links.json
```

**If missing:** Create it with sample data (see below)

---

### **Fix 2: Verify Dockerfile Copies File**

Check your `Dockerfile`:

```dockerfile
# ✅ CORRECT
COPY . .

# ❌ WRONG (excludes data/)
COPY bot/ /app/bot/
COPY main.py /app/
# (data/ not copied!)
```

**Solution:** Use `COPY . .` to copy everything

---

### **Fix 3: Check .dockerignore**

If you have `.dockerignore`, ensure it doesn't exclude `data/`:

```bash
# ❌ BAD .dockerignore
data/
*.json

# ✅ GOOD .dockerignore
.git/
__pycache__/
*.pyc
.env
```

---

### **Fix 4: Manual File Verification**

After deployment, exec into container:

```bash
# Railway
railway run bash

# Docker
docker exec -it container_name bash

# Check file
ls -la /app/data/adjust_links.json
cat /app/data/adjust_links.json
```

---

## 📄 Sample adjust_links.json

Create `data/adjust_links.json`:

```json
[
  {
    "symbol": "BTC/USDT",
    "adjust_link": "https://mudrex.go.link/1Yogo"
  },
  {
    "symbol": "ETH/USDT",
    "adjust_link": "https://mudrex.go.link/kmYNX"
  },
  {
    "symbol": "ELSA/USDT",
    "adjust_link": "https://mudrex.go.link/ELSA"
  }
]
```

**Important:**
- Use slash format: `"BTC/USDT"` (NOT `"BTCUSDT"`)
- Bot automatically handles both formats via normalization
- Valid JSON syntax (no trailing commas)

---

## 🔧 Advanced Diagnostics

### **Enable Debug Logging**

Set environment variable:
```bash
LOG_LEVEL=DEBUG
```

You'll see detailed lookups:
```bash
🔍 Searching for adjust_links.json...
✅ Found file: /app/data/adjust_links.json
✅ Found adjust link: ELSA/USDT -> https://mudrex.go.link/ELSA
```

---

### **Test Module Load Manually**

```python
# In Python console
from bot.services import adjust_links

# Check cache
print(adjust_links.get_cache_stats())
# Output: {'total_entries': 21, 'cache_loaded': True, ...}

# Test lookup
link = adjust_links.find_adjust_link("BTC/USDT")
print(link)
# Output: https://mudrex.go.link/1Yogo
```

---

### **Force Reload**

If you update `adjust_links.json` after deployment:

```bash
# Restart bot to reload
railway restart

# Or in Python console
from bot.services import adjust_links
adjust_links.load_adjust_links()
```

---

## 📊 Expected Log Output (Success)

```bash
============================================================
🔍 STARTUP DIAGNOSTICS - ADJUST LINKS VERIFICATION
============================================================

🚀 Initializing adjust_links module...

============================================================
🔍 VERIFYING ADJUST LINKS JSON FILE
============================================================
📁 Checking 5 possible file locations:

1. /app/data/adjust_links.json
   Absolute: /app/data/adjust_links.json
   Exists: ✅ YES
   Is file: ✅ YES
   Size: 1234 bytes
   Content length: 1234 chars
   JSON valid: ✅ YES
   Entries: 21 adjust links
   Sample entries:
      - BTC/USDT: https://mudrex.go.link/1Yogo
      - ETH/USDT: https://mudrex.go.link/kmYNX
      - BNB/USDT: https://mudrex.go.link/3G8Mh

============================================================
📥 LOADING ADJUST LINKS
============================================================
📂 Loading from: /app/data/adjust_links.json
✅ JSON parsed: 21 entries
✅ Loaded 21 adjust links
✅ Cache size: 42 entries (including normalized)

📊 Sample adjust links:
   1. BTC/USDT: https://mudrex.go.link/1Yogo
   2. BTCUSDT: https://mudrex.go.link/1Yogo
   3. ETH/USDT: https://mudrex.go.link/kmYNX
   4. ETHUSDT: https://mudrex.go.link/kmYNX
   5. BNB/USDT: https://mudrex.go.link/3G8Mh
============================================================

✅ Adjust links module initialized successfully

📊 Adjust Links Cache Statistics:
   Total entries: 42
   Cache loaded: ✅ YES
   Sample symbols: BTC/USDT, BTCUSDT, ETH/USDT, ETHUSDT, BNB/USDT

✅ Adjust links module loaded successfully
============================================================
```

---

## ❌ Expected Log Output (Failure)

```bash
============================================================
🔍 VERIFYING ADJUST LINKS JSON FILE
============================================================
📁 Checking 5 possible file locations:

1. /app/bot/services/../../data/adjust_links.json
   Absolute: /app/data/adjust_links.json
   Exists: ❌ NO

2. /app/data/adjust_links.json
   Absolute: /app/data/adjust_links.json
   Exists: ❌ NO

... (all locations fail)

============================================================
❌ ADJUST LINKS FILE NOT FOUND IN ANY LOCATION
============================================================

📂 Current working directory: /app
📂 Directory contents:
   📁 DIR : bot
   📄 FILE: main.py
   📄 FILE: requirements.txt
   📄 FILE: Dockerfile

📂 Checking 'data/' directory:
   ❌ data/ directory does NOT EXIST

============================================================
💡 SOLUTIONS:
============================================================
1. Ensure data/adjust_links.json is in your repository
2. Check your Dockerfile COPY commands
3. Verify file is not in .dockerignore
4. Use absolute path in Docker: COPY data/ /app/data/
============================================================

❌ Cannot load adjust links - file not found
⚠️  Bot will continue but NO ALERTS will have adjust links!
```

---

## 🚀 Deployment Checklist

Before deploying:

- [ ] `data/adjust_links.json` exists in repository
- [ ] File has valid JSON syntax
- [ ] Symbols use slash format: `BTC/USDT`
- [ ] Dockerfile uses `COPY . .`
- [ ] No `.dockerignore` excluding `data/`
- [ ] Git tracked: `git ls-files data/adjust_links.json` shows file
- [ ] File size > 0 bytes

After deploying:

- [ ] Check logs for "✅ Loaded N adjust links"
- [ ] Verify cache size > 0
- [ ] Test alert includes adjust link button
- [ ] Manual verification: exec into container, check file exists

---

## 🆘 Still Not Working?

### **1. Check Docker Build Logs**

```bash
railway logs --build

# Look for:
✅ adjust_links.json FOUND
📄 File size: 1234 bytes
```

### **2. Check Runtime Logs**

```bash
railway logs

# Look for:
✅ Loaded 21 adjust links
```

### **3. Test Locally First**

```bash
# Build Docker image locally
docker build -t price-bot .

# Check file in image
docker run -it price-bot ls -la /app/data/

# Run bot locally
docker run -it --env-file .env price-bot
```

### **4. Force Rebuild**

Sometimes cached layers cause issues:

```bash
# Railway
railway up --force

# Docker
docker build --no-cache -t price-bot .
```

---

## 📞 Contact Support

If still experiencing issues after following this guide:

1. Share full startup logs (first 100 lines)
2. Share Docker build logs
3. Confirm file exists in repository: `git ls-files data/adjust_links.json`
4. Share output of: `ls -la data/`

---

## ✅ Success Indicators

You'll know it's working when:

1. **Startup logs show:**
   ```
   ✅ Loaded 21 adjust links
   ✅ Cache size: 42 entries
   ✅ Adjust links module loaded successfully
   ```

2. **Alert messages include:**
   ```
   🚨 BTC/USDT Alert!
   📈 UP 12.5% in 24h
   ...
   [📊 View Chart] ← Button with adjust link
   ```

3. **Debug logs show:**
   ```
   ✅ Found adjust link: BTC/USDT -> https://mudrex.go.link/1Yogo
   ```

---

**This comprehensive diagnostic system will identify exactly why adjust links aren't loading!** 🚀
