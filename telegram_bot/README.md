# ISONER Telegram Bot

This is the Telegram Bot component of the ISONER Modern Chatbot system. It serves as the user interface for interacting with the ISONER system through Telegram.

## Features

- Handles user messages and forwards them to the ISONER backend
- Receives responses from the ISONER system via Pub/Sub
- Supports various message types (text, photos, documents, locations)
- Provides basic commands (/start, /help)

## Setup

1. Create a `.env` file based on `.env.example`:
   ```
   cp .env.example .env
   ```

2. Edit the `.env` file with your actual credentials:
   - Get a Telegram Bot token from [@BotFather](https://t.me/BotFather)
   - Set your GCP Project ID
   - Set the path to your GCP credentials file

3. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

4. Run the bot:
   ```
   python bot.py
   ```

## Docker Deployment

You can also run the bot using Docker:

```
docker build -t isoner-telegram-bot .
docker run -v /path/to/credentials.json:/app/credentials.json --env-file .env isoner-telegram-bot
```

## Architecture

The bot communicates with the ISONER system through the API Gateway for sending messages and listens to a Pub/Sub subscription for receiving responses.

```
User <-> Telegram <-> Telegram Bot <-> API Gateway <-> ISONER System
                                    <-- Pub/Sub <--
``` 