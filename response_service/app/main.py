from fastapi import FastAPI
import os
import json
import logging
import threading
from google.cloud import pubsub_v1
from concurrent.futures import TimeoutError
from supabase import create_client, Client
from datetime import datetime

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="ISONER Chatbot Response Service")

# Supabase setup
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    logger.error("Supabase credentials not provided")
    raise ValueError("SUPABASE_URL and SUPABASE_KEY must be set")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# GCP Pub/Sub setup
PROJECT_ID = os.getenv("GCP_PROJECT_ID")
PROCESSED_MESSAGES_TOPIC = os.getenv("PUBSUB_PROCESSED_MESSAGES_TOPIC", "processed-messages")
PROCESSED_MESSAGES_SUBSCRIPTION = os.getenv("PUBSUB_PROCESSED_MESSAGES_SUBSCRIPTION", "processed-messages-response-sub")
OUTGOING_MESSAGES_TOPIC = os.getenv("PUBSUB_OUTGOING_MESSAGES_TOPIC", "outgoing-messages")

publisher = pubsub_v1.PublisherClient()
subscriber = pubsub_v1.SubscriberClient()

outgoing_topic_path = publisher.topic_path(PROJECT_ID, OUTGOING_MESSAGES_TOPIC)
subscription_path = subscriber.subscription_path(PROJECT_ID, PROCESSED_MESSAGES_SUBSCRIPTION)

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

def format_response(processed_data):
    """Format the response based on the processed data"""
    try:
        # Extract data
        message_id = processed_data.get('message_id')
        conversation_id = processed_data.get('conversation_id')
        user_id = processed_data.get('user_id')
        original_content = processed_data.get('original_content')
        processed_result = processed_data.get('processed_result', {})
        
        intent = processed_result.get('intent', 'general_query')
        entities = processed_result.get('entities', [])
        response_text = processed_result.get('response', 'I apologize, but I could not process your request.')
        
        # Format response based on intent
        if intent == 'hotel_booking':
            # Check if we have location entity
            location = next((entity['value'] for entity in entities if entity['type'] == 'location'), None)
            if location:
                response_text = f"I'd be happy to help you book a hotel in {location}. Could you please provide your check-in and check-out dates?"
            else:
                response_text = "I'd be happy to help you book a hotel. Could you please provide the location and dates for your stay?"
        
        elif intent == 'hotel_search':
            # Check if we have location entity
            location = next((entity['value'] for entity in entities if entity['type'] == 'location'), None)
            if location:
                response_text = f"I'll search for hotels in {location} for you. Please wait a moment..."
                
                # Here we could trigger an external data request
                # For simplicity, we'll just include a placeholder
                response_text += "\n\nHere are some top hotels in the area:\n1. Grand Hotel\n2. Luxury Suites\n3. Comfort Inn"
            else:
                response_text = "I can help you search for hotels. Could you please specify the location you're interested in?"
        
        # Store bot response in Supabase
        bot_message_data = {
            "conversation_id": conversation_id,
            "sender_type": "bot",
            "content": response_text,
            "content_type": "text",
            "created_at": datetime.now().isoformat()
        }
        supabase.table("messages").insert(bot_message_data).execute()
        
        # Update original message as processed
        supabase.table("messages").update({"processed": True}).eq("id", message_id).execute()
        
        # Publish outgoing message
        outgoing_message = {
            'conversation_id': conversation_id,
            'user_id': user_id,
            'content': response_text,
            'content_type': 'text',
            'timestamp': datetime.now().isoformat()
        }
        
        publisher.publish(
            outgoing_topic_path,
            data=json.dumps(outgoing_message).encode("utf-8")
        )
        
        return True
    except Exception as e:
        logger.error(f"Error formatting response: {e}")
        return False

def callback(message):
    """Callback for Pub/Sub messages"""
    try:
        data = json.loads(message.data.decode("utf-8"))
        logger.info(f"Received processed message: {data['message_id']}")
        
        success = format_response(data)
        if success:
            message.ack()
        else:
            message.nack()
    except Exception as e:
        logger.error(f"Error in callback: {e}")
        message.nack()

def start_subscriber():
    """Start the Pub/Sub subscriber"""
    streaming_pull_future = subscriber.subscribe(
        subscription_path, callback=callback
    )
    logger.info(f"Listening for messages on {subscription_path}")
    
    try:
        streaming_pull_future.result()
    except TimeoutError:
        streaming_pull_future.cancel()
        streaming_pull_future.result()
    except Exception as e:
        logger.error(f"Error in subscriber: {e}")

@app.on_event("startup")
async def startup_event():
    """Start the Pub/Sub subscriber on startup"""
    threading.Thread(target=start_subscriber, daemon=True).start()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8005)