import telegram
import asyncio
import logging
import aiohttp
import os

logger = logging.getLogger('src.telegram')

class TelegramBot:
    def __init__(self, config, message_queue):
        self.config = config
        self.message_queue = message_queue
        self.bot = telegram.Bot(token=config['telegram_token'])

    def format_discord_message(self, content):
        """Format Discord message for Telegram Markdown with newline after first colon."""
        # Split the message at the first colon
        if ':' in content:
            prefix, message = content.split(':', 1)
            # Convert Discord Markdown syntax to Telegram
            message = message.replace('**', '*')  # Bold: from **text** to *text*
            message = message.replace('__', '_')  # Italic: from __text__ to _text_
            # Combine with a newline
            return f"{prefix}:\n{message.strip()}"
        return content

    async def send_text_message(self, content):
        """Send a text message to Telegram with Markdown parsing."""
        formatted_content = self.format_discord_message(content)
        logger.info(f"Sending text to Telegram: {formatted_content}")
        try:
            await self.bot.send_message(
                chat_id=self.config['telegram_chat_id'],
                text=formatted_content,
                parse_mode=telegram.constants.ParseMode.MARKDOWN
            )
            logger.info("Text message sent successfully")
        except telegram.error.TelegramError as e:
            logger.error(f"Failed to send message: {e}")

    async def send_attachment(self, url, caption, session):
        """Send an attachment (photo or document) to Telegram with Markdown caption."""
        formatted_caption = self.format_discord_message(caption) if caption else None
        async with session.get(url) as response:
            if response.status == 200:
                file_data = await response.read()
                file_name = url.split('/')[-1].split('?')[0]

                try:
                    if file_name.lower().endswith(('.png', '.jpg', '.jpeg', '.gif')):
                        logger.info(f"Sending photo to Telegram: {file_name}")
                        await self.bot.send_photo(
                            chat_id=self.config['telegram_chat_id'],
                            photo=file_data,
                            caption=formatted_caption,
                            parse_mode=telegram.constants.ParseMode.MARKDOWN
                        )
                    else:
                        logger.info(f"Sending document to Telegram: {file_name}")
                        await self.bot.send_document(
                            chat_id=self.config['telegram_chat_id'],
                            document=file_data,
                            filename=file_name,
                            caption=formatted_caption,
                            parse_mode=telegram.constants.ParseMode.MARKDOWN
                        )
                    logger.info("Attachment sent successfully")
                except telegram.error.TelegramError as e:
                    logger.error(f"Failed to send attachment: {e}")
            else:
                logger.error(f"Failed to download attachment: {url} - Status: {response.status}")

    async def send_messages(self):
        """Process messages from the queue and send to Telegram."""
        async with aiohttp.ClientSession() as session:
            while True:
                item = await self.message_queue.get()
                try:
                    if item['type'] == 'text':
                        await self.send_text_message(item['content'])
                    elif item['type'] == 'attachment':
                        await self.send_attachment(item['url'], item['caption'], session)
                except Exception as e:
                    logger.error(f"Error processing message: {e}")
                self.message_queue.task_done()

    async def run(self):
        logger.info("Starting Telegram src")
        await self.send_messages()