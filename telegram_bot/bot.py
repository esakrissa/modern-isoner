#!/usr/bin/env python3
"""
Telegram Bot for ISONER Modern Chatbot
This script runs a Telegram bot that interacts with the ISONER system.
"""

import os
import json
import logging
import asyncio
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import httpx
from google.cloud import pubsub_v1
from concurrent.futures import TimeoutError

# Load environment variables
load_dotenv()

# Setup logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Environment variables
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
API_GATEWAY_URL = os.getenv("API_GATEWAY_URL", "http://localhost:8000")
GCP_PROJECT_ID = os.getenv("GCP_PROJECT_ID")
OUTGOING_MESSAGES_TOPIC = os.getenv("PUBSUB_OUTGOING_MESSAGES_TOPIC", "outgoing-messages")
OUTGOING_MESSAGES_SUBSCRIPTION = os.getenv("PUBSUB_OUTGOING_MESSAGES_SUBSCRIPTION", "outgoing-messages-telegram-sub")

# Check if token is provided
if not TELEGRAM_BOT_TOKEN:
    logger.error("No Telegram bot token provided")
    raise ValueError("TELEGRAM_BOT_TOKEN environment variable is required")

# GCP Pub/Sub setup
subscriber = pubsub_v1.SubscriberClient()
subscription_path = subscriber.subscription_path(GCP_PROJECT_ID, OUTGOING_MESSAGES_SUBSCRIPTION)

# Dictionary to store active conversations
active_conversations = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a message when the command /start is issued."""
    user = update.effective_user
    await update.message.reply_html(
        f"Hi {user.mention_html()}! I'm the ISONER Chatbot. How can I help you today?"
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a message when the command /help is issued."""
    await update.message.reply_text(
        "I can help you with various tasks. Just send me a message and I'll do my best to assist you."
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle incoming messages from users."""
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    message_text = update.message.text
    
    # Store the chat_id for later use when receiving responses
    active_conversations[str(user_id)] = chat_id
    
    try:
        # Send message to API Gateway
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{API_GATEWAY_URL}/messages/send",
                json={
                    "user_id": str(user_id),
                    "content": message_text,
                    "content_type": "text"
                },
                headers={"Content-Type": "application/json"}
            )
            
            if response.status_code != 200:
                logger.error(f"Error sending message to API Gateway: {response.text}")
                await update.message.reply_text(
                    "Sorry, I'm having trouble processing your message. Please try again later."
                )
            else:
                # Let the user know we're processing their message
                await update.message.reply_text("Processing your message...")
                
    except Exception as e:
        logger.error(f"Error communicating with API Gateway: {e}")
        await update.message.reply_text(
            "Sorry, I'm having trouble connecting to my backend. Please try again later."
        )

async def process_responses():
    """Process responses from Pub/Sub and send them to users."""
    def callback(message):
        try:
            data = json.loads(message.data.decode("utf-8"))
            user_id = data.get("user_id")
            content = data.get("content")
            content_type = data.get("content_type", "text")
            
            if user_id and content:
                chat_id = active_conversations.get(user_id)
                if chat_id:
                    # Use asyncio to send the message
                    asyncio.create_task(send_telegram_message(chat_id, content, content_type))
                else:
                    logger.warning(f"Received message for unknown user: {user_id}")
            
            message.ack()
        except Exception as e:
            logger.error(f"Error processing Pub/Sub message: {e}")
            message.ack()  # Ack anyway to avoid reprocessing problematic messages
    
    streaming_pull_future = subscriber.subscribe(subscription_path, callback=callback)
    logger.info(f"Listening for messages on {subscription_path}")
    
    # Keep the thread alive
    try:
        streaming_pull_future.result()
    except TimeoutError:
        streaming_pull_future.cancel()
        streaming_pull_future.result()
    except Exception as e:
        logger.error(f"Error in Pub/Sub subscription: {e}")
        streaming_pull_future.cancel()
        streaming_pull_future.result()

async def send_telegram_message(chat_id, content, content_type):
    """Send a message to a Telegram chat."""
    try:
        bot = Application.get_current().bot
        if content_type == "text":
            await bot.send_message(chat_id=chat_id, text=content)
        elif content_type == "photo":
            # Assuming content is a URL to a photo
            await bot.send_photo(chat_id=chat_id, photo=content)
        elif content_type == "document":
            # Assuming content is a URL to a document
            await bot.send_document(chat_id=chat_id, document=content)
        elif content_type == "location":
            # Assuming content is a dict with latitude and longitude
            location = json.loads(content) if isinstance(content, str) else content
            await bot.send_location(
                chat_id=chat_id, 
                latitude=location.get("latitude"), 
                longitude=location.get("longitude")
            )
        else:
            logger.warning(f"Unsupported content type: {content_type}")
            await bot.send_message(
                chat_id=chat_id, 
                text=f"Received content of unsupported type: {content_type}"
            )
    except Exception as e:
        logger.error(f"Error sending Telegram message: {e}")

def main() -> None:
    """Start the bot."""
    # Create the Application
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    # Add handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # Start the Pub/Sub listener in a separate task
    asyncio.create_task(asyncio.to_thread(process_responses))

    # Run the bot until the user presses Ctrl-C
    application.run_polling()

if __name__ == "__main__":
    main() 