from fastapi import FastAPI, Request, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
import httpx
import os
from typing import Dict, Any
import logging
from .middleware import AuthMiddleware

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

# HTTP client
http_client = httpx.AsyncClient()

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

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