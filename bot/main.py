"""
Main Entry Point with Token Masking Security Fix
"""

import logging
import sys

# CRITICAL: Setup logging FIRST before any other imports
# This ensures errors during config validation are logged
logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    level=logging.INFO,
    handlers=[logging.StreamHandler(sys.stdout)]
)

logger = logging.getLogger(__name__)
logger.info("🔄 Starting Price Alert Bot...")

# Now import config (this runs validation)
try:
    from bot import config
except SystemExit:
    logger.error("❌ Configuration validation failed! Check environment variables.")
    raise
except Exception as e:
    logger.error(f"❌ Failed to load config: {e}")
    raise

# Update log level from config
logging.getLogger().setLevel(getattr(logging, config.LOG_LEVEL))

# Now import other modules
from telegram.ext import Application, CommandHandler
from bot.services.price_monitor import PriceMonitor
from bot.services.database import initialize_database, seed_initial_pairs
from bot.handlers import admin_commands, control_commands, stats_commands

# 🔐 SECURITY FIX: Prevent token exposure in logs
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)
logging.getLogger("telegram").setLevel(logging.WARNING)


async def post_init(application: Application):
    """Initialize services after bot starts"""
    logger.info("🚀 Bot started successfully")

    # Start price monitoring service
    monitor = PriceMonitor(application.bot)
    monitor.start()

    # Set reference for control commands (for /status, /test, /pause, /resume)
    control_commands.set_price_monitor(monitor)

    logger.info("✅ Price monitor started")


def main():
    """Main entry point"""
    try:
        # Initialize database schema (creates tables if not exist)
        logger.info("📦 Initializing database...")
        initialize_database()

        # Seed initial trading pairs if database is empty
        seed_initial_pairs()

        # Create application
        application = (
            Application.builder()
            .token(config.TELEGRAM_BOT_TOKEN)
            .post_init(post_init)
            .build()
        )

        # Register command handlers
        application.add_handler(CommandHandler("start", control_commands.start_command))
        application.add_handler(CommandHandler("help", control_commands.help_command))

        # Admin commands
        application.add_handler(CommandHandler("addnew", admin_commands.addnew_command))
        application.add_handler(CommandHandler("removepair", admin_commands.removepair_command))
        application.add_handler(CommandHandler("cooldown", admin_commands.cooldown_command))
        application.add_handler(CommandHandler("reseed", admin_commands.reseed_command))
        application.add_handler(CommandHandler("turnoff", admin_commands.turnoff_command))
        application.add_handler(CommandHandler("automap", admin_commands.automap_command))
        application.add_handler(CommandHandler("ai", admin_commands.ai_toggle_command))
        application.add_handler(CommandHandler("nativebybit", admin_commands.nativebybit_command))
        application.add_handler(CommandHandler("seedlinks", admin_commands.seedlinks_command))
        application.add_handler(CommandHandler("volume", admin_commands.volume_command))
        application.add_handler(CommandHandler("interval", admin_commands.interval_command))
        application.add_handler(CommandHandler("show", admin_commands.show_command))

        # Control commands
        application.add_handler(CommandHandler("pause", control_commands.pause_command))
        application.add_handler(CommandHandler("resume", control_commands.resume_command))
        application.add_handler(CommandHandler("status", control_commands.status_command))
        application.add_handler(CommandHandler("test", control_commands.test_command))

        # Stats commands
        application.add_handler(CommandHandler("stats", stats_commands.stats_command))
        application.add_handler(CommandHandler("listpairs", stats_commands.listpairs_command))

        # Start the bot
        logger.info("🤖 Starting Telegram bot...")
        application.run_polling(allowed_updates=["message", "callback_query"])

    except Exception as e:
        logger.error(f"❌ Bot startup failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
