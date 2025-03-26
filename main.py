import asyncio
import json
import logging
from logging.handlers import TimedRotatingFileHandler
import os
import time
from app.discord_bot import DiscordBot
from app.telegram_bot import TelegramBot

# Ensure logs directory exists
log_dir = 'logs'
os.makedirs(log_dir, exist_ok=True)

# Configure logging with rotation
log_handler = TimedRotatingFileHandler(
    filename=os.path.join(log_dir, 'bot.log'),
    when='midnight',  # Rotate at midnight
    interval=1,       # Every day
    backupCount=2     # Keep 2 days of logs
)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[log_handler, logging.StreamHandler()]
)
logger = logging.getLogger('bot')

# Load configuration
with open('config.json', 'r') as f:
    config = json.load(f)

# Shared message queue
message_queue = asyncio.Queue()

async def clean_old_logs():
    """Delete log files older than 2 days."""
    while True:
        now = time.time()
        if os.path.exists(log_dir):
            for filename in os.listdir(log_dir):
                file_path = os.path.join(log_dir, filename)
                if os.path.isfile(file_path) and 'bot.log' in filename:
                    file_age = now - os.path.getmtime(file_path)
                    if file_age > 2 * 24 * 60 * 60:  # 2 days in seconds
                        os.remove(file_path)
                        logger.info(f"Deleted old log file: {file_path}")
        await asyncio.sleep(24 * 60 * 60)  # Check once a day

async def main():
    # Initialize bots
    discord_bot = DiscordBot(config, message_queue)
    telegram_bot = TelegramBot(config, message_queue)

    # Run both bots and cleanup concurrently
    await asyncio.gather(
        discord_bot.run(),
        telegram_bot.run(),
        clean_old_logs()
    )

if __name__ == "__main__":
    asyncio.run(main())