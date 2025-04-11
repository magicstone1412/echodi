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
        self.bot = telegram.Bot(token=config['telegram']['token'])

    def _split_message_by_colon(self, content):
        """Split message by the first colon and return prefix and message."""
        if ':' in content:
            prefix, message = content.split(':', 1)
            return prefix, message
        return None, content

    def _remove_discord_emojis(self, message):
        """Remove Discord custom emojis from the message."""
        return re.sub(r'<a?:\w+:\d+>', '', message)

    def _convert_markdown_to_html(self, message):
        """Convert Discord Markdown to Telegram HTML."""
        message = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', message)              # Bold
        message = re.sub(r'__(.*?)__', r'<i>\1</i>', message)                  # Italic
        message = re.sub(r'~~(.*?)~~', r'<s>\1</s>', message)                  # Strikethrough
        message = re.sub(r'\|\|(.*?)\|\|', r'<span class="tg-spoiler">\1</span>', message)  # Spoiler
        message = re.sub(r'`([^`]+)`', r'<code>\1</code>', message)            # Inline code
        message = re.sub(
            r'```(\w+)?\n(.*?)\n```',
            lambda m: f'<pre><code class="language-{m.group(1)}">{m.group(2)}</code></pre>' if m.group(1) else f'<pre>{m.group(2)}</pre>',
            message,
            flags=re.DOTALL
        )
        return message.strip()

    def format_discord_message(self, content):
        """Convert Discord Markdown to Telegram HTML with newline after first colon."""
        prefix, message = self._split_message_by_colon(content)
        message = self._remove_discord_emojis(message)
        message = self._convert_markdown_to_html(message)
        return f"{prefix}:\n{message}" if prefix else message

    async def send_text_message(self, content):
        """Send a text message to Telegram with HTML parsing."""
        formatted_content = self.format_discord_message(content)
        logger.info(f"Sending text to Telegram (converted to HTML): {formatted_content}")
        try:
            await self.bot.send_message(
                chat_id=self.config['telegram']['chat_id'],
                text=formatted_content,
                parse_mode=telegram.constants.ParseMode.HTML
            )
            logger.info("Text message sent successfully")
        except telegram.error.TelegramError as e:
            logger.error(f"Failed to send message: {e}")

    def _determine_file_type(self, file_name):
        """Determine the file type based on extension."""
        file_name = file_name.lower()
        if file_name.endswith(('.png', '.jpg', '.jpeg', '.gif')):
            return 'photo', 10  # Type, max size in MB
        elif file_name.endswith(('.mp4', '.mov', '.avi')):
            return 'video', 50
        else:
            return 'document', 50

    async def _send_large_file_fallback(self, formatted_caption, url, file_type):
        """Send a fallback text message with a link for large files."""
        logger.info(f"{file_type.capitalize()} too large, sending caption and hidden URL")
        await self.send_text_message(f"{formatted_caption}\n{file_type.capitalize()}: <a href=\"{url}\">Link</a>")

    async def send_attachment(self, url, caption, session):
        """Send an attachment (photo, video, or document) to Telegram."""
        formatted_caption = self.format_discord_message(caption) if caption else "Attachment"
        async with session.get(url) as response:
            if response.status != 200:
                logger.error(f"Failed to download attachment: {url} - Status: {response.status}")
                return

            file_data = await response.read()
            file_size = len(file_data) / (1024 * 1024)  # Size in MB
            file_name = url.split('/')[-1].split('?')[0]
            file_type, max_size = self._determine_file_type(file_name)

            try:
                if file_size > max_size:
                    logger.error(f"{file_type.capitalize()} too large: {file_name} ({file_size:.2f} MB) exceeds Telegram's {max_size} MB limit")
                    await self._send_large_file_fallback(formatted_caption, url, file_type)
                    return

                logger.info(f"Sending {file_type} to Telegram: {file_name}")
                if file_type == 'photo':
                    await self.bot.send_photo(
                        chat_id=self.config['telegram']['chat_id'],
                        photo=file_data,
                        caption=formatted_caption,
                        parse_mode=telegram.constants.ParseMode.HTML
                    )
                elif file_type == 'video':
                    await self.bot.send_video(
                        chat_id=self.config['telegram']['chat_id'],
                        video=file_data,
                        filename=file_name,
                        caption=formatted_caption,
                        parse_mode=telegram.constants.ParseMode.HTML
                    )
                else:  # document
                    await self.bot.send_document(
                        chat_id=self.config['telegram']['chat_id'],
                        document=file_data,
                        filename=file_name,
                        caption=formatted_caption,
                        parse_mode=telegram.constants.ParseMode.HTML
                    )
                logger.info("Attachment sent successfully")
            except telegram.error.TelegramError as e:
                logger.error(f"Failed to send attachment: {e}")

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
        """Start the Telegram bot."""
        logger.info("Starting Telegram bot")
        await self.send_messages()