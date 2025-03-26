import telegram
import asyncio
import logging

logger = logging.getLogger('bot.telegram')

class TelegramBot:
    def __init__(self, config, message_queue):
        self.config = config
        self.message_queue = message_queue
        self.bot = telegram.Bot(token=config['telegram_token'])

    async def send_messages(self):
        """Process messages from the queue and send to Telegram."""
        while True:
            content = await self.message_queue.get()
            try:
                logger.info(f"Sending to Telegram: {content}")
                await self.bot.send_message(chat_id=self.config['telegram_chat_id'], text=content)
                logger.info("Message sent successfully")
            except Exception as e:
                logger.error(f"Error sending to Telegram: {e}")
            self.message_queue.task_done()

    async def run(self):
        logger.info("Starting Telegram bot")
        await self.send_messages()