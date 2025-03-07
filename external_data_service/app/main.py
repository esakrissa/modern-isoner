from fastapi import FastAPI, HTTPException
import httpx
import redis
import json
import os
import logging
from typing import Optional

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="ISONER Chatbot External Data Service")

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

# RapidAPI setup
RAPIDAPI_KEY = os.getenv("RAPIDAPI_KEY")
if not RAPIDAPI_KEY:
    logger.error("RapidAPI key not provided")
    raise ValueError("RAPIDAPI_KEY must be set")

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

@app.get("/hotels/search")
async def search_hotels(location: str, check_in: Optional[str] = None, check_out: Optional[str] = None):
    try:
        # Check cache
        cache_key = f"hotels:search:{location}:{check_in}:{check_out}"
        cached_result = redis_client.get(cache_key)
        
        if cached_result:
            logger.info(f"Cache hit for hotel search: {location}")
            return json.loads(cached_result)
        
        # Call RapidAPI
        url = "https://hotels4.p.rapidapi.com/locations/v2/search"
        
        headers = {
            "X-RapidAPI-Key": RAPIDAPI_KEY,
            "X-RapidAPI-Host": "hotels4.p.rapidapi.com"
        }
        
        params = {"query": location, "locale": "en_US", "currency": "USD"}
        
        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=headers, params=params)
            response.raise_for_status()
            result = response.json()
            
            # Cache result
            redis_client.setex(
                cache_key,
                3600,  # 1 hour
                json.dumps(result)
            )
            
            return result
    except httpx.HTTPError as e:
        logger.error(f"Error calling RapidAPI: {e}")
        raise HTTPException(status_code=500, detail=f"Error fetching hotel data: {str(e)}")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")

@app.get("/hotels/{hotel_id}")
async def get_hotel_details(hotel_id: str):
    try:
        # Check cache
        cache_key = f"hotels:details:{hotel_id}"
        cached_result = redis_client.get(cache_key)
        
        if cached_result:
            logger.info(f"Cache hit for hotel details: {hotel_id}")
            return json.loads(cached_result)
        
        # Call RapidAPI
        url = "https://hotels4.p.rapidapi.com/properties/get-details"
        
        headers = {
            "X-RapidAPI-Key": RAPIDAPI_KEY,
            "X-RapidAPI-Host": "hotels4.p.rapidapi.com"
        }
        
        params = {
            "id": hotel_id,
            "locale": "en_US",
            "currency": "USD"
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=headers, params=params)
            response.raise_for_status()
            result = response.json()
            
            # Cache result
            redis_client.setex(
                cache_key,
                3600 * 24,  # 24 hours
                json.dumps(result)
            )
            
            return result
    except httpx.HTTPError as e:
        logger.error(f"Error calling RapidAPI: {e}")
        raise HTTPException(status_code=500, detail=f"Error fetching hotel details: {str(e)}")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8004)