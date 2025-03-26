import asyncio
import json
import logging
from logging.handlers import TimedRotatingFileHandler
import os
import time
import aiofiles  # Add to requirements.txt
from bot.discord_bot import DiscordBot
from bot.telegram_bot import TelegramBot

log_dir = 'logs'
os.makedirs(log_dir, exist_ok=True)

log_handler = TimedRotatingFileHandler(
    filename=os.path.join(log_dir, 'bot.log'),
    when='midnight',
    interval=1,
    backupCount=2
)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[log_handler, logging.StreamHandler()]
)
logger = logging.getLogger('bot')

with open('config.json', 'r') as f:
    config = json.load(f)

message_queue = asyncio.Queue()
queue_file = os.path.join(log_dir, 'queue.json')

async def load_queue():
    """Load persisted queue on startup."""
    if os.path.exists(queue_file):
        async with aiofiles.open(queue_file, 'r') as f:
            data = await f.read()
            if data:
                items = json.loads(data)
                for item in items:
                    await message_queue.put(item)
                logger.info(f"Loaded {len(items)} items from queue")

async def save_queue():
    """Save queue to file periodically."""
    while True:
        items = []
        while not message_queue.empty():
            items.append(await message_queue.get())
        if items:
            async with aiofiles.open(queue_file, 'w') as f:
                await f.write(json.dumps(items))
            for item in items:
                await message_queue.put(item)  # Re-queue items
            logger.info(f"Saved {len(items)} items to queue")
        await asyncio.sleep(60)  # Save every minute

async def clean_old_logs():
    while True:
        now = time.time()
        if os.path.exists(log_dir):
            for filename in os.listdir(log_dir):
                file_path = os.path.join(log_dir, filename)
                if os.path.isfile(file_path) and 'bot.log' in filename:
                    file_age = now - os.path.getmtime(file_path)
                    if file_age > 2 * 24 * 60 * 60:
                        os.remove(file_path)
                        logger.info(f"Deleted old log file: {file_path}")
        await asyncio.sleep(24 * 60 * 60)

async def main():
    discord_bot = DiscordBot(config, message_queue)
    telegram_bot = TelegramBot(config, message_queue)
    await load_queue()  # Load queue on startup
    await asyncio.gather(
        discord_bot.run(),
        telegram_bot.run(),
        clean_old_logs(),
        save_queue()  # Periodically save queue
    )

if __name__ == "__main__":
    asyncio.run(main())