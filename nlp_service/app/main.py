from fastapi import FastAPI
import os
import json
import logging
import redis
import openai
from google.cloud import pubsub_v1
from concurrent.futures import TimeoutError
import threading

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="ISONER Chatbot NLP Service")

# Redis setup
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
REDIS_DB = int(os.getenv("REDIS_DB", "0"))
REDIS_PASSWORD = os.getenv("REDIS_PASSWORD", "")

redis_client = redis.Redis(
    host=REDIS_HOST,
    port=REDIS_PORT,
    db=REDIS_DB,
    password=REDIS_PASSWORD,
    decode_responses=True
)

# OpenAI setup
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    logger.error("OpenAI API key not provided")
    raise ValueError("OPENAI_API_KEY must be set")

openai.api_key = OPENAI_API_KEY

# GCP Pub/Sub setup
PROJECT_ID = os.getenv("GCP_PROJECT_ID")
INCOMING_MESSAGES_TOPIC = os.getenv("PUBSUB_INCOMING_MESSAGES_TOPIC", "incoming-messages")
INCOMING_MESSAGES_SUBSCRIPTION = os.getenv("PUBSUB_INCOMING_MESSAGES_SUBSCRIPTION", "incoming-messages-nlp-sub")
PROCESSED_MESSAGES_TOPIC = os.getenv("PUBSUB_PROCESSED_MESSAGES_TOPIC", "processed-messages")

publisher = pubsub_v1.PublisherClient()
subscriber = pubsub_v1.SubscriberClient()

processed_topic_path = publisher.topic_path(PROJECT_ID, PROCESSED_MESSAGES_TOPIC)
subscription_path = subscriber.subscription_path(PROJECT_ID, INCOMING_MESSAGES_SUBSCRIPTION)

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

def process_message(message_data):
    """Process a message using OpenAI API"""
    try:
        # Check cache
        cache_key = f"nlp:{message_data['content']}"
        cached_result = redis_client.get(cache_key)
        
        if cached_result:
            logger.info(f"Cache hit for message {message_data['message_id']}")
            result = json.loads(cached_result)
        else:
            logger.info(f"Processing message {message_data['message_id']} with OpenAI")
            
            # Process with OpenAI
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are a helpful assistant for a hotel booking service."},
                    {"role": "user", "content": message_data['content']}
                ]
            )
            
            # Extract intent and entities (simplified)
            content = response.choices[0].message.content
            
            # Simple intent detection
            intent = "general_query"
            if "book" in message_data['content'].lower() or "reservation" in message_data['content'].lower():
                intent = "hotel_booking"
            elif "cancel" in message_data['content'].lower():
                intent = "cancel_booking"
            elif "search" in message_data['content'].lower() or "find" in message_data['content'].lower():
                intent = "hotel_search"
                
            # Simple entity extraction (very basic)
            entities = []
            if "tomorrow" in message_data['content'].lower():
                entities.append({"type": "date", "value": "tomorrow"})
            if "new york" in message_data['content'].lower():
                entities.append({"type": "location", "value": "new york"})
                
            result = {
                'intent': intent,
                'entities': entities,
                'response': content
            }
            
            # Cache result
            redis_client.setex(
                cache_key,
                3600,  # 1 hour
                json.dumps(result)
            )
        
        # Publish processed message
        processed_message = {
            'message_id': message_data['message_id'],
            'conversation_id': message_data['conversation_id'],
            'user_id': message_data['user_id'],
            'original_content': message_data['content'],
            'processed_result': result
        }
        
        publisher.publish(
            processed_topic_path,
            data=json.dumps(processed_message).encode("utf-8")
        )
        
        return True
    except Exception as e:
        logger.error(f"Error processing message: {e}")
        return False

def callback(message):
    """Callback for Pub/Sub messages"""
    try:
        data = json.loads(message.data.decode("utf-8"))
        logger.info(f"Received message: {data['message_id']}")
        
        success = process_message(data)
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
    uvicorn.run(app, host="0.0.0.0", port=8003)