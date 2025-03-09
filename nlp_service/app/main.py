from fastapi import FastAPI
import os
import json
import logging
import redis
import openai
from google.cloud import pubsub_v1
from concurrent.futures import TimeoutError
import threading
import hashlib
import time

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="ISONER Chatbot NLP Service")

# Redis setup
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
REDIS_DB = int(os.getenv("REDIS_DB", "0"))
REDIS_PASSWORD = os.getenv("REDIS_PASSWORD", "")
REDIS_CACHE_TTL = int(os.getenv("REDIS_CACHE_TTL", "3600"))  # Default 1 hour

# Redis connection with retries
def get_redis_connection(max_retries=5, retry_delay=2):
    retries = 0
    while retries < max_retries:
        try:
            client = redis.Redis(
                host=REDIS_HOST,
                port=REDIS_PORT,
                db=REDIS_DB,
                password=REDIS_PASSWORD,
                decode_responses=True,
                socket_timeout=5,
                socket_connect_timeout=5
            )
            # Test connection
            client.ping()
            logger.info(f"Successfully connected to Redis at {REDIS_HOST}:{REDIS_PORT}")
            return client
        except redis.ConnectionError as e:
            retries += 1
            logger.warning(f"Redis connection attempt {retries} failed: {e}")
            if retries < max_retries:
                time.sleep(retry_delay)
            else:
                logger.error(f"Failed to connect to Redis after {max_retries} attempts")
                # Return None or raise an exception based on your preference
                return None

# Initialize Redis with retry logic
redis_client = get_redis_connection()
if not redis_client:
    logger.warning("Running without Redis cache - performance may be affected")

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
    # Check Redis connection
    redis_status = "connected" if redis_client and redis_client.ping() else "disconnected"
    return {
        "status": "healthy",
        "redis_status": redis_status,
        "openai_api": "configured"
    }

def create_cache_key(message_content, user_id=None):
    """Create deterministic cache key from message content"""
    # Add user ID to make cache keys user-specific if needed
    content_to_hash = message_content
    if user_id:
        content_to_hash = f"{user_id}:{message_content}"
    
    # Create a deterministic hash for the content
    hash_obj = hashlib.md5(content_to_hash.encode('utf-8'))
    return f"nlp:response:{hash_obj.hexdigest()}"

def get_from_cache(key):
    """Try to get data from Redis cache with error handling"""
    if not redis_client:
        return None
    
    try:
        cached_data = redis_client.get(key)
        if cached_data:
            return json.loads(cached_data)
    except (redis.RedisError, json.JSONDecodeError) as e:
        logger.warning(f"Error retrieving from cache: {e}")
    
    return None

def save_to_cache(key, data, ttl=REDIS_CACHE_TTL):
    """Save data to Redis cache with error handling"""
    if not redis_client:
        return False
    
    try:
        redis_client.setex(
            key,
            ttl,
            json.dumps(data)
        )
        return True
    except (redis.RedisError, TypeError) as e:
        logger.warning(f"Error saving to cache: {e}")
        return False

def process_message(message_data):
    """Process a message using OpenAI API with enhanced caching"""
    try:
        # Generate cache key
        cache_key = create_cache_key(
            message_data['content'], 
            message_data.get('user_id')
        )
        
        # Try to get from cache
        cached_result = get_from_cache(cache_key)
        
        if cached_result:
            logger.info(f"Cache hit for message {message_data['message_id']}")
            result = cached_result
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
                'response': content,
                'model': 'gpt-3.5-turbo',
                'cached': False,
                'timestamp': time.time()
            }
            
            # Cache result
            cache_saved = save_to_cache(cache_key, result)
            if cache_saved:
                logger.info(f"Cached result for message {message_data['message_id']}")
        
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
    port = int(os.getenv("PORT", 8080))
    uvicorn.run(app, host="0.0.0.0", port=port)