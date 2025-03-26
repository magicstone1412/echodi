import telegram
import asyncio
import logging
import aiohttp
import os

logger = logging.getLogger ( 'bot.telegram' )


class TelegramBot:
    def __init__ ( self, config, message_queue ):
        self.config = config
        self.message_queue = message_queue
        self.bot = telegram.Bot ( token=config [ 'telegram_token' ] )

    async def send_messages ( self ):
        """Process messages from the queue and send to Telegram."""
        async with aiohttp.ClientSession () as session:
            while True:
                item = await self.message_queue.get ()
                try:
                    if item [ 'type' ] == 'text':
                        # Send text message
                        logger.info ( f"Sending text to Telegram: {item [ 'content' ]}" )
                        await self.bot.send_message ( chat_id=self.config [ 'telegram_chat_id' ],
                                                      text=item [ 'content' ] )
                        logger.info ( "Text message sent successfully" )
                    elif item [ 'type' ] == 'attachment':
                        # Download attachment
                        async with session.get ( item [ 'url' ] ) as response:
                            if response.status == 200:
                                file_data = await response.read ()
                                file_name = item [ 'url' ].split ( '/' ) [ -1 ].split ( '?' ) [ 0 ]  # Extract filename

                                # Determine file type and send accordingly
                                if file_name.lower ().endswith ( ('.png', '.jpg', '.jpeg', '.gif') ):
                                    logger.info ( f"Sending photo to Telegram: {file_name}" )
                                    await self.bot.send_photo (
                                        chat_id=self.config [ 'telegram_chat_id' ],
                                        photo=file_data,
                                        caption=item [ 'caption' ]
                                    )
                                else:
                                    logger.info ( f"Sending document to Telegram: {file_name}" )
                                    await self.bot.send_document (
                                        chat_id=self.config [ 'telegram_chat_id' ],
                                        document=file_data,
                                        filename=file_name,
                                        caption=item [ 'caption' ]
                                    )
                                logger.info ( "Attachment sent successfully" )
                            else:
                                logger.error (
                                    f"Failed to download attachment: {item [ 'url' ]} - Status: {response.status}" )
                except Exception as e:
                    logger.error ( f"Error processing message: {e}" )
                self.message_queue.task_done ()

    async def run ( self ):
        logger.info ( "Starting Telegram bot" )
        await self.send_messages ()