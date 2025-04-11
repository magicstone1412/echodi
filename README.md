# echodi

A bot forward messages from discord channels to a Telegram group

## Prerequisites

### Bot Tokens:

#### Discord Bot Token:
- Create a bot at [Discord Developer Portal](https://discord.com/developers/applications)
- Enable **"Message Content Intent"** in the Bot settings
- Invite the bot to your server with appropriate permissions

#### Telegram Bot Token:
- Create a bot via **BotFather** on Telegram
- Get the token from **BotFather**

#### Telegram Channel ID:
- Add your Telegram bot as an **administrator** to your channel
- Get the channel ID:
  - Starts with `@` for public channels
  - Use a bot API call for private channels

## Run app using Docker

### Configuration file for bot settings.

```json
{
  "discord": {
    "token": "your_discord_bot_token",
    "channel_ids": [123456789012345678, <integer>, ...]
  },
  "telegram": {
    "token": "your_telegram_bot_token",
    "chat_id": "your_telegram_channel_id"
  }
}
```

```commandline
docker run -d \
    --name echodi \
	-v /root/docker/echodi/config.json:/app/config.json \
	--restart unless-stopped \
  skywirex/echodi
```

```commandline
EchoDi/
├── app/
│   ├── __init__.py
│   ├── discord_bot.py
│   └── telegram_bot.py
├── logs/
│   ├── bot.log           (created automatically)
│   ├── bot.log.2025-03-25 (example rotated log, created after rotation)
│   └── bot.log.2025-03-26 (example rotated log, created after rotation)
├── config.json
├── main.py
└── requirements.txt
```