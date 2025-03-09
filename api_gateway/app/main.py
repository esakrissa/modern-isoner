from fastapi import FastAPI, Request, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
import httpx
import os
from typing import Dict, Any, Optional
import logging
from .middleware import AuthMiddleware
import redis
import json
import time

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="ISONER Chatbot API Gateway")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Update this in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Auth middleware
app.add_middleware(AuthMiddleware)

# Service URLs
AUTH_SERVICE_URL = os.getenv("AUTH_SERVICE_URL", "http://localhost:8001")
MESSAGE_SERVICE_URL = os.getenv("MESSAGE_SERVICE_URL", "http://localhost:8002")
EXTERNAL_DATA_SERVICE_URL = os.getenv("EXTERNAL_DATA_SERVICE_URL", "http://localhost:8004")

# Redis setup for caching
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
REDIS_DB = int(os.getenv("REDIS_DB", "0"))
REDIS_PASSWORD = os.getenv("REDIS_PASSWORD", "")

# Initialize Redis client
redis_client = redis.Redis(
    host=REDIS_HOST,
    port=REDIS_PORT,
    db=REDIS_DB,
    password=REDIS_PASSWORD,
    decode_responses=True
)

# Cache TTL settings (in seconds)
AUTH_CACHE_TTL = 300  # 5 minutes
MESSAGE_CACHE_TTL = 60  # 1 minute
EXTERNAL_DATA_CACHE_TTL = 1800  # 30 minutes

# HTTP client
http_client = httpx.AsyncClient()

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

# Cache middleware for API responses
async def get_cached_response(cache_key: str) -> Optional[dict]:
    """Get cached response if available"""
    try:
        cached = redis_client.get(cache_key)
        if cached:
            logger.info(f"Cache hit for {cache_key}")
            return json.loads(cached)
        return None
    except Exception as e:
        logger.error(f"Error retrieving from cache: {e}")
        return None

async def cache_response(cache_key: str, response_data: dict, ttl: int) -> None:
    """Cache API response"""
    try:
        redis_client.setex(cache_key, ttl, json.dumps(response_data))
        logger.info(f"Cached response for {cache_key} with TTL {ttl}s")
    except Exception as e:
        logger.error(f"Error caching response: {e}")

@app.post("/api/v1/auth/{path:path}")
async def auth_proxy(path: str, request: Request):
    """Proxy requests to Auth Service"""
    body = await request.json()
    try:
        response = await http_client.post(
            f"{AUTH_SERVICE_URL}/{path}",
            json=body,
            headers=dict(request.headers)
        )
        return response.json()
    except httpx.HTTPError as e:
        logger.error(f"Error proxying to auth service: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")

@app.post("/api/v1/messages/{path:path}")
async def message_proxy(path: str, request: Request):
    """Proxy requests to Message Service"""
    body = await request.json()
    try:
        # Forward user ID from token
        headers = dict(request.headers)
        headers["X-User-ID"] = request.state.user_id
        
        response = await http_client.post(
            f"{MESSAGE_SERVICE_URL}/{path}",
            json=body,
            headers=headers
        )
        return response.json()
    except httpx.HTTPError as e:
        logger.error(f"Error proxying to message service: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")

@app.get("/api/v1/external/{path:path}")
async def external_data_proxy(path: str, request: Request):
    """Proxy requests to External Data Service"""
    params = dict(request.query_params)
    try:
        # Forward user ID from token
        headers = dict(request.headers)
        headers["X-User-ID"] = request.state.user_id
        
        response = await http_client.get(
            f"{EXTERNAL_DATA_SERVICE_URL}/{path}",
            params=params,
            headers=headers
        )
        return response.json()
    except httpx.HTTPError as e:
        logger.error(f"Error proxying to external data service: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")

@app.get("/api/v1/admin/{path:path}")
async def admin_proxy(path: str, request: Request):
    """Proxy requests to Admin routes"""
    try:
        # Forward user ID from token
        headers = dict(request.headers)
        headers["X-User-ID"] = request.state.user_id
        
        # Determine which service to route to based on path
        if path.startswith("users"):
            service_url = f"{AUTH_SERVICE_URL}/admin/{path}"
        elif path.startswith("conversations"):
            service_url = f"{MESSAGE_SERVICE_URL}/admin/{path}"
        else:
            raise HTTPException(status_code=404, detail="Not Found")
        
        response = await http_client.get(
            service_url,
            headers=headers,
            params=dict(request.query_params)
        )
        return response.json()
    except httpx.HTTPError as e:
        logger.error(f"Error proxying to admin routes: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")

@app.on_event("shutdown")
async def shutdown_event():
    await http_client.aclose()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)