# 🤖 Telegram Price Alert Bot

Automated cryptocurrency price monitoring bot with real-time alerts for significant price movements.

## 🎯 Features

- **Automatic Price Monitoring**: Monitors 478+ trading pairs every 30 seconds using REST API
- **Smart Thresholds**: Multi-tier alert system (+10%, +30%, +60%, +100%, then every +50%)
- **Session-Based Alerts**: Daily reset at 00:00 UTC, prevents duplicate alerts
- **Volume Filtering**: Only alerts for pairs with $5M+ 24h volume
- **Dual API Support**: Bybit (primary) with Binance fallback via CCXT
- **Clean Alerts**: Professional formatting with dynamic CTA buttons
- **Admin Controls**: Bulk add/remove pairs, pause/resume scanner, view stats

## 📋 Requirements

- Python 3.11+
- PostgreSQL database
- Telegram Bot Token
- Railway account (for deployment)

## 🚀 Quick Start

### 1. Clone Repository

```bash
git clone <repository-url>
cd PriceAlertBot
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure Environment

Copy `.env.example` to `.env` and fill in your credentials:

```bash
cp .env.example .env
```

Required variables:
- `TELEGRAM_BOT_TOKEN`: Your bot token from @BotFather
- `TELEGRAM_GROUP_ID`: Your Telegram group ID
- `PRICE_ALERTS_TOPIC_ID`: Topic ID for alerts
- `ADMIN_USER_IDS`: Comma-separated admin user IDs
- `DATABASE_URL`: PostgreSQL connection string

### 4. Initialize Database

```bash
psql -U postgres -d your_database -f data/init_db.sql
```

### 5. Run Bot

```bash
python -m bot.main
```

## 🐳 Docker Deployment

### Build Image

```bash
docker build -t price-alert-bot .
```

### Run Container

```bash
docker run -d \
  --name price-bot \
  --env-file .env \
  price-alert-bot
```

## 🚂 Railway Deployment

### 1. Create Railway Project

1. Connect your GitHub repository
2. Add PostgreSQL service
3. Deploy from `main` branch

### 2. Set Environment Variables

In Railway dashboard, add:

```
TELEGRAM_BOT_TOKEN=your_bot_token
TELEGRAM_GROUP_ID=-1001234567890
PRICE_ALERTS_TOPIC_ID=12345
ADMIN_USER_IDS=123456789,987654321
DATABASE_URL=${{Postgres.DATABASE_URL}}
```

### 3. Verify Deployment

Check logs for:
```
✅ All dependencies OK
✅ All required environment variables present
✅ Price monitor started (30s interval, REST API)
🤖 Starting Telegram bot...
```

## 📱 Bot Commands

### General Commands

- `/start` - Welcome message
- `/help` - Show available commands
- `/status` - Check scanner status
- `/stats` - View bot statistics
- `/listpairs` - Show all monitored pairs

### Admin Commands

- `/addnew SYMBOL link` - Add single pair
- `/addnew SYM1 link1 SYM2 link2` - Bulk add pairs
- `/removepair SYMBOL` - Remove pair
- `/cooldown 30m` - Set alert cooldown
- `/pause` - Pause scanner
- `/resume` - Resume scanner

## 🎨 Alert Format

```
🚀 BIG PUMP! (+30.2%)

💰 BTC
📊 $95,000 → $123,690
📈 +30.2% (24h)

[🚀 DON'T MISS OUT - BTC]
```

**Dynamic CTA Buttons:**
- 100%+: 🔥 EXPLOSIVE GAINS
- 50-99%: 🚀 DON'T MISS OUT
- 30-49%: 📈 CATCH THE PUMP
- 10-29%: 💰 TRADE NOW

## 🔧 Configuration

### Alert Thresholds

**Gainers:** +10%, +30%, +60%, +80%, +100%, then every +50%
**Losers:** -10%, -30%, -60%, -80%, -100%, then every -50%

### Filters

- **Volume:** Minimum $5,000,000 (24h)
- **Adjust Link:** Required for alerts
- **Cooldown:** Configurable per-pair delay

### Scanner Settings

- **Interval:** 30 seconds (configurable)
- **Batch Size:** 50 pairs per request
- **Session Reset:** Daily at 00:00 UTC

## 📂 Project Structure

```
PriceAlertBot/
├── Dockerfile                  # Docker configuration
├── requirements.txt            # Python dependencies
├── .env.example               # Environment template
├── .gitignore                 # Git ignore rules
├── README.md                  # This file
│
├── bot/
│   ├── __init__.py
│   ├── main.py                # Entry point
│   ├── config.py              # Configuration
│   │
│   ├── services/
│   │   ├── price_monitor.py   # Background scanner
│   │   ├── price_fetcher.py   # CCXT API wrapper
│   │   ├── alert_checker.py   # Threshold logic
│   │   ├── session_manager.py # Daily reset handler
│   │   └── database.py        # PostgreSQL operations
│   │
│   ├── handlers/
│   │   ├── admin_commands.py  # Admin command handlers
│   │   ├── control_commands.py # Bot control handlers
│   │   └── stats_commands.py  # Statistics handlers
│   │
│   ├── models/
│   │   ├── pair.py           # ActivePair model
│   │   ├── alert.py          # Alert model
│   │   └── snapshot.py       # PriceSnapshot model
│   │
│   └── utils/
│       ├── formatters.py     # Message formatting
│       ├── validators.py     # Input validation
│       └── helpers.py        # Utility functions
│
└── data/
    ├── init_db.sql           # Database schema
    └── seed_pairs.csv        # Initial pairs data
```

## 🔒 Security Features

- **Token Masking**: Prevents bot token exposure in logs
- **Admin-Only Commands**: Restricted access to sensitive operations
- **Input Validation**: Sanitizes all user inputs
- **SQL Injection Protection**: Parameterized queries
- **Environment Variables**: Secrets stored securely

## 🐛 Troubleshooting

### Bot Not Starting

Check environment variables:
```bash
python -c "from bot import config"
```

### Database Connection Failed

Verify `DATABASE_URL`:
```bash
psql $DATABASE_URL -c "SELECT 1"
```

### No Alerts Firing

1. Check scanner status: `/status`
2. Verify pairs have Adjust links: `/listpairs`
3. Check volume filter (minimum $5M)
4. Review logs for errors

### API Errors

- CCXT automatically handles rate limiting
- Bybit → Binance fallback is automatic
- Check API status at status.bybit.com

## 📊 Database Schema

### Tables

- `active_pairs` - Trading pairs with Adjust links
- `price_snapshots` - Historical price data
- `alert_history` - Fired alerts per session
- `bot_config` - Configuration key-value store
- `scanner_logs` - Performance monitoring

### Indexes

- Symbol + timestamp for fast price lookups
- Session date for alert deduplication
- Status for active pair filtering

## 🔄 Session Reset Logic

**Daily Reset at 00:00 UTC:**
1. New base price captured for all pairs
2. Alert history preserved (by session_date)
3. Old snapshots cleaned (25+ hours)
4. Scanner logs archived (30+ days)

## 📈 Performance

- **Scan Time:** ~5-10 seconds for 478 pairs
- **Memory Usage:** ~150-200 MB
- **API Calls:** 10-12 requests per scan (batch fetching)
- **Database Queries:** Optimized with indexes

## 🤝 Contributing

1. Fork the repository
2. Create feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open Pull Request

## 📝 License

This project is licensed under the MIT License.

## 🙏 Acknowledgments

- [python-telegram-bot](https://github.com/python-telegram-bot/python-telegram-bot) - Telegram Bot API wrapper
- [CCXT](https://github.com/ccxt/ccxt) - Cryptocurrency exchange API
- [APScheduler](https://github.com/agronholm/apscheduler) - Job scheduling

## 📧 Support

For issues and questions:
- Open an issue on GitHub
- Contact admin via Telegram

---

**Built with ❤️ for automated crypto trading alerts**
