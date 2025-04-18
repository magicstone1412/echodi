import discord
from discord.ext import commands
import asyncio
import logging

logger = logging.getLogger('src.discord')

class DiscordBot:
    def __init__(self, config, message_queue):
        self.config = config
        self.message_queue = message_queue
        intents = discord.Intents.default()
        intents.messages = True
        intents.message_content = True
        self.bot = commands.Bot(command_prefix='!', intents=intents)

    async def setup(self):
        @self.bot.event
        async def on_ready():
            logger.info(f'Discord Bot connected as {self.bot.user}')
            logger.info(f"Monitoring channels: {self.config['discord']['channel_ids']}")

        @self.bot.event
        async def on_message ( message ):
            logger.info ( f"Received message in channel {message.channel.id} from {message.author}" )
            if message.author == self.bot.user:
                logger.info ( "Ignoring message from self" )
                return

            if message.channel.id in self.config [ 'discord' ] [ 'channel_ids' ]:
                logger.info ( f"Message matches monitored channel {message.channel.id}" )
                channel_name = message.channel.name
                content = f"From {channel_name} ({message.author.name}): {message.content}" if message.content else f"From {channel_name} ({message.author.name})"

                # Handle embeds for forwarded messages or rich content
                if not message.content and message.embeds:
                    embed_content = [ ]
                    for embed in message.embeds:
                        if embed.title:
                            embed_content.append ( f"Title: {embed.title}" )
                        if embed.description:
                            embed_content.append ( f"Description: {embed.description}" )
                        if embed.fields:
                            for field in embed.fields:
                                embed_content.append ( f"{field.name}: {field.value}" )
                    if embed_content:
                        content += "\n" + "\n".join ( embed_content )
                        logger.info ( f"Added embed content: {content}" )

                if message.attachments:
                    for attachment in message.attachments:
                        # Queue attachment URL separately
                        await self.message_queue.put (
                            { 'type': 'attachment', 'url': attachment.url, 'caption': content }
                        )
                        logger.info ( f"Queued attachment: {attachment.url} with caption: {content}" )
                else:
                    # Queue text-only message
                    await self.message_queue.put ( { 'type': 'text', 'content': content } )
                    logger.info ( f"Queued text message: {content}" )

    async def run(self):
        logger.info("Starting Discord bot")
        await self.setup()
        await self.bot.start(self.config['discord']['token'])