from fastapi import FastAPI, HTTPException, Depends, Header
from pydantic import BaseModel
from typing import Optional, List
import uuid
from datetime import datetime
import os
import json
import logging
from google.cloud import pubsub_v1
from supabase import create_client, Client

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="ISONER Chatbot Message Service")

# Supabase setup
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    logger.error("Supabase credentials not provided")
    raise ValueError("SUPABASE_URL and SUPABASE_KEY must be set")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# GCP Pub/Sub setup
PROJECT_ID = os.getenv("GCP_PROJECT_ID")
INCOMING_MESSAGES_TOPIC = os.getenv("PUBSUB_INCOMING_MESSAGES_TOPIC", "incoming-messages")

publisher = pubsub_v1.PublisherClient()
topic_path = publisher.topic_path(PROJECT_ID, INCOMING_MESSAGES_TOPIC)

class Message(BaseModel):
    content: str
    content_type: str = "text"
    conversation_id: Optional[str] = None

class Conversation(BaseModel):
    id: str
    user_id: str
    started_at: datetime
    last_message_at: datetime

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

@app.post("/send")
async def send_message(message: Message, authorization: Optional[str] = Header(None)):
    try:
        # Extract user_id from token (simplified)
        user_id = "user-123"  # In production, extract from JWT token
        
        # Create conversation if not exists
        conversation_id = message.conversation_id
        if not conversation_id:
            # Create new conversation
            conversation_data = {
                "user_id": user_id,
                "started_at": datetime.now().isoformat(),
                "last_message_at": datetime.now().isoformat(),
                "status": "active"
            }
            result = supabase.table("conversations").insert(conversation_data).execute()
            conversation_id = result.data[0]["id"]
        else:
            # Update last_message_at
            supabase.table("conversations").update({
                "last_message_at": datetime.now().isoformat()
            }).eq("id", conversation_id).execute()
        
        # Store message in Supabase
        message_id = str(uuid.uuid4())
        message_data = {
            "id": message_id,
            "conversation_id": conversation_id,
            "sender_type": "user",
            "content": message.content,
            "content_type": message.content_type,
            "created_at": datetime.now().isoformat(),
            "processed": False
        }
        supabase.table("messages").insert(message_data).execute()
        
        # Publish message to Pub/Sub
        pubsub_message = {
            "message_id": message_id,
            "conversation_id": conversation_id,
            "user_id": user_id,
            "content": message.content,
            "content_type": message.content_type,
            "timestamp": datetime.now().isoformat()
        }
        
        publisher.publish(
            topic_path, 
            data=json.dumps(pubsub_message).encode("utf-8")
        )
        
        return {
            "message_id": message_id,
            "conversation_id": conversation_id,
            "status": "sent"
        }
    except Exception as e:
        logger.error(f"Error sending message: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/conversations/{conversation_id}/messages")
async def get_messages(conversation_id: str, authorization: Optional[str] = Header(None)):
    try:
        # Extract user_id from token (simplified)
        user_id = "user-123"  # In production, extract from JWT token
        
        # Check if conversation belongs to user
        conversation = supabase.table("conversations").select("*").eq("id", conversation_id).eq("user_id", user_id).execute()
        
        if not conversation.data:
            raise HTTPException(status_code=404, detail="Conversation not found")
        
        # Get messages
        messages = supabase.table("messages").select("*").eq("conversation_id", conversation_id).order("created_at").execute()
        
        return {"messages": messages.data}
    except Exception as e:
        logger.error(f"Error getting messages: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8002)