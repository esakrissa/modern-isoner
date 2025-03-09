#!/usr/bin/env python3
"""
Telegram Bot for Modern ISONER Chatbot
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
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

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
WEBHOOK_MODE = os.getenv("TELEGRAM_WEBHOOK_MODE", "false").lower() == "true"
PORT = int(os.getenv("PORT", "8080"))

# Check if token is provided
if not TELEGRAM_BOT_TOKEN:
    logger.error("No Telegram bot token provided")
    raise ValueError("TELEGRAM_BOT_TOKEN environment variable is required")

# GCP Pub/Sub setup
subscriber = pubsub_v1.SubscriberClient()
subscription_path = subscriber.subscription_path(GCP_PROJECT_ID, OUTGOING_MESSAGES_SUBSCRIPTION)

# Dictionary to store active conversations
active_conversations = {}

# Create FastAPI app for webhook mode
app = FastAPI(title="Telegram Bot Webhook")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a message when the command /start is issued."""
    user = update.effective_user
    await update.message.reply_html(
        f"Hi {user.mention_html()}! I'm the Modern ISONER  Chatbot. How can I help you today?",
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a message when the command /help is issued."""
    await update.message.reply_text("I can help you with hotel bookings and information. Just ask me anything!")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle incoming messages from users."""
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    message_text = update.message.text
    
    logger.info(f"Received message from user {user_id}: {message_text}")
    
    # Store conversation in active conversations
    if chat_id not in active_conversations:
        active_conversations[chat_id] = {
            "user_id": user_id,
            "messages": []
        }
    
    active_conversations[chat_id]["messages"].append({
        "role": "user",
        "content": message_text
    })
    
    # Send message to API Gateway
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{API_GATEWAY_URL}/api/v1/messages",
                json={
                    "user_id": str(user_id),
                    "chat_id": str(chat_id),
                    "content": message_text
                }
            )
            
            if response.status_code == 202:
                await update.message.reply_text("I'm processing your request...")
            else:
                logger.error(f"Error sending message to API Gateway: {response.status_code} {response.text}")
                await update.message.reply_text("Sorry, I'm having trouble processing your request. Please try again later.")
    except Exception as e:
        logger.error(f"Error communicating with API Gateway: {e}")
        await update.message.reply_text("Sorry, I'm having trouble connecting to my services. Please try again later.")

async def process_responses():
    """Process responses from Pub/Sub subscription."""
    
    def callback(message):
        """Process a Pub/Sub message."""
        try:
            data = json.loads(message.data.decode("utf-8"))
            logger.info(f"Received response message: {data}")
            
            chat_id = data.get("chat_id")
            content = data.get("content")
            content_type = data.get("content_type", "text")
            
            if chat_id and content:
                # Use asyncio to call the async function from this sync callback
                loop = asyncio.get_event_loop()
                loop.create_task(send_telegram_message(chat_id, content, content_type))
                
                # Store bot response in conversation history
                if chat_id in active_conversations:
                    active_conversations[chat_id]["messages"].append({
                        "role": "assistant",
                        "content": content
                    })
            
            message.ack()
        except Exception as e:
            logger.error(f"Error processing Pub/Sub message: {e}")
            message.nack()
    
    # Start the Pub/Sub subscriber
    streaming_pull_future = subscriber.subscribe(
        subscription_path, callback=callback
    )
    logger.info(f"Listening for messages on {subscription_path}")
    
    try:
        # Keep the subscriber alive
        while True:
            await asyncio.sleep(60)
    except Exception as e:
        logger.error(f"Error in Pub/Sub subscriber: {e}")
        streaming_pull_future.cancel()
        streaming_pull_future.result()

async def send_telegram_message(chat_id, content, content_type):
    """Send a message to a Telegram chat."""
    try:
        # Create a bot instance
        from telegram import Bot
        bot = Bot(token=TELEGRAM_BOT_TOKEN)
        
        if content_type == "text":
            await bot.send_message(chat_id=chat_id, text=content)
        elif content_type == "image":
            # Handle image URLs
            await bot.send_photo(chat_id=chat_id, photo=content)
        elif content_type == "document":
            # Handle document URLs
            await bot.send_document(chat_id=chat_id, document=content)
        else:
            # Default to text
            await bot.send_message(chat_id=chat_id, text=content)
            
        logger.info(f"Sent message to chat {chat_id}")
    except Exception as e:
        logger.error(f"Error sending Telegram message: {e}")

@app.post("/webhook")
async def webhook(request: Request):
    """Handle webhook requests from Telegram."""
    update_data = await request.json()
    update = Update.de_json(update_data, None)
    
    # Create Application instance
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    
    # Add handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    # Process the update
    await application.process_update(update)
    
    return JSONResponse(content={"status": "ok"})

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "mode": "webhook" if WEBHOOK_MODE else "polling"}

def main() -> None:
    """Start the bot."""
    if WEBHOOK_MODE:
        # Start FastAPI server for webhook mode
        import uvicorn
        
        # Start the Pub/Sub listener in a separate thread
        asyncio.create_task(asyncio.to_thread(process_responses))
        
        # Run the FastAPI server
        logger.info(f"Starting webhook server on port {PORT}")
        uvicorn.run(app, host="0.0.0.0", port=PORT)
    else:
        # Create the Application for polling mode
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