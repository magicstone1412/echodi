import telegram
import asyncio
import logging
import aiohttp
import os
import re

logger = logging.getLogger('src.telegram')

class TelegramBot:
    def __init__(self, config, message_queue):
        self.config = config
        self.message_queue = message_queue
        self.bot = telegram.Bot(token=config['telegram_token'])

    def format_discord_message(self, content):
        """Convert Discord Markdown to Telegram HTML with newline after first colon."""
        if ':' in content:
            prefix, message = content.split(':', 1)
            # Convert Discord Markdown to Telegram HTML
            message = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', message)              # Bold
            message = re.sub(r'__(.*?)__', r'<i>\1</i>', message)                  # Italic (assuming underline not intended)
            message = re.sub(r'~~(.*?)~~', r'<s>\1</s>', message)                  # Strikethrough
            message = re.sub(r'\|\|(.*?)\|\|', r'<span class="tg-spoiler">\1</span>', message)  # Spoiler
            message = re.sub(r'`([^`]+)`', r'<code>\1</code>', message)            # Inline code
            # Code block with optional language
            message = re.sub(r'```(\w+)?\n(.*?)\n```', lambda m: f'<pre><code class="language-{m.group(1)}">{m.group(2)}</code></pre>' if m.group(1) else f'<pre>{m.group(2)}</pre>', message, flags=re.DOTALL)
            # Combine with a newline
            return f"{prefix}:\n{message.strip()}"
        return content

    async def send_text_message(self, content):
        """Send a text message to Telegram with HTML parsing after converting from Discord Markdown."""
        formatted_content = self.format_discord_message(content)
        logger.info(f"Sending text to Telegram (converted to HTML): {formatted_content}")
        try:
            await self.bot.send_message(
                chat_id=self.config['telegram_chat_id'],
                text=formatted_content,
                parse_mode=telegram.constants.ParseMode.HTML
            )
            logger.info("Text message sent successfully")
        except telegram.error.TelegramError as e:
            logger.error(f"Failed to send message: {e}")

    async def send_attachment(self, url, caption, session):
        """Send an attachment to Telegram with HTML caption after converting from Discord Markdown."""
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
                            parse_mode=telegram.constants.ParseMode.HTML
                        )
                    else:
                        logger.info(f"Sending document to Telegram: {file_name}")
                        await self.bot.send_document(
                            chat_id=self.config['telegram_chat_id'],
                            document=file_data,
                            filename=file_name,
                            caption=formatted_caption,
                            parse_mode=telegram.constants.ParseMode.HTML
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