from fastapi import FastAPI, HTTPException, Depends, Header, Request
from pydantic import BaseModel
from supabase import create_client, Client
import os
from typing import Optional, List
import logging
import jwt
import uuid
from datetime import datetime
import redis
import json

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="ISONER Chatbot Auth Service")

# Supabase setup
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
JWT_SECRET = os.getenv("JWT_SECRET", "your-secret-key")  # In production, use a secure secret key

if not SUPABASE_URL or not SUPABASE_KEY:
    logger.error("Supabase credentials not provided")
    raise ValueError("SUPABASE_URL and SUPABASE_KEY must be set")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

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
USER_CACHE_TTL = 300  # 5 minutes
TOKEN_CACHE_TTL = 3600  # 1 hour

class UserRegister(BaseModel):
    email: str
    password: str
    name: Optional[str] = None

class UserLogin(BaseModel):
    email: str
    password: str

class UserResponse(BaseModel):
    id: str
    email: str
    name: Optional[str] = None

class RoleResponse(BaseModel):
    id: str
    name: str
    description: Optional[str] = None

async def get_user_id_from_header(x_user_id: Optional[str] = Header(None)):
    """Get user ID from X-User-ID header"""
    if not x_user_id:
        raise HTTPException(status_code=401, detail="X-User-ID header missing")
    return x_user_id

# Helper function to cache user data
def cache_user_data(user_id: str, user_data: dict) -> None:
    """Cache user data for faster access"""
    try:
        redis_client.setex(f"user:{user_id}", USER_CACHE_TTL, json.dumps(user_data))
        logger.info(f"Cached user data for user_id: {user_id}")
    except Exception as e:
        logger.error(f"Error caching user data: {e}")

# Helper function to get cached user data
def get_cached_user(user_id: str) -> Optional[dict]:
    """Get cached user data if available"""
    try:
        cached = redis_client.get(f"user:{user_id}")
        if cached:
            logger.info(f"Cache hit for user_id: {user_id}")
            return json.loads(cached)
        return None
    except Exception as e:
        logger.error(f"Error retrieving cached user data: {e}")
        return None

# Helper function to cache token validation
def cache_token_validation(token: str, user_id: str) -> None:
    """Cache token validation result"""
    try:
        redis_client.setex(f"token:{token}", TOKEN_CACHE_TTL, user_id)
        logger.info(f"Cached token validation for user_id: {user_id}")
    except Exception as e:
        logger.error(f"Error caching token validation: {e}")

# Helper function to get cached token validation
def get_cached_token_validation(token: str) -> Optional[str]:
    """Get cached token validation if available"""
    try:
        cached = redis_client.get(f"token:{token}")
        if cached:
            logger.info(f"Cache hit for token validation")
            return cached
        return None
    except Exception as e:
        logger.error(f"Error retrieving cached token validation: {e}")
        return None

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

@app.post("/register")
async def register(user: UserRegister):
    try:
        # Register user with Supabase Auth
        auth_response = supabase.auth.sign_up({
            "email": user.email,
            "password": user.password
        })
        
        # Store additional user data in Supabase
        user_data = {
            "id": auth_response.user.id,
            "email": user.email,
            "name": user.name or user.email.split("@")[0],
            "created_at": auth_response.user.created_at
        }
        
        supabase.table("users").insert(user_data).execute()
        
        # Cache user data
        cache_user_data(auth_response.user.id, user_data)
        
        # Assign default 'user' role
        default_role = supabase.from_("roles").select("id").eq("name", "user").execute()
        if default_role.data:
            supabase.from_("user_roles").insert({
                "user_id": auth_response.user.id,
                "role_id": default_role.data[0]["id"]
            }).execute()
        
        return {
            "message": "User registered successfully",
            "user_id": auth_response.user.id
        }
    except Exception as e:
        logger.error(f"Error registering user: {e}")
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/login")
async def login(user: UserLogin):
    try:
        # Login user with Supabase Auth
        auth_response = supabase.auth.sign_in_with_password({
            "email": user.email,
            "password": user.password
        })
        
        # Cache user data and token validation
        user_data = {
            "id": auth_response.user.id,
            "email": auth_response.user.email
        }
        cache_user_data(auth_response.user.id, user_data)
        cache_token_validation(auth_response.session.access_token, auth_response.user.id)
        
        return {
            "message": "Login successful",
            "access_token": auth_response.session.access_token,
            "refresh_token": auth_response.session.refresh_token,
            "user": {
                "id": auth_response.user.id,
                "email": auth_response.user.email
            }
        }
    except Exception as e:
        logger.error(f"Error logging in user: {e}")
        raise HTTPException(status_code=401, detail="Invalid credentials")

@app.post("/logout")
async def logout(authorization: Optional[str] = Header(None)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Authorization header required")
    
    try:
        token = authorization.replace("Bearer ", "")
        
        # Invalidate token in cache
        redis_client.delete(f"token:{token}")
        
        # Sign out from Supabase
        supabase.auth.sign_out()
        return {"message": "Logout successful"}
    except Exception as e:
        logger.error(f"Error logging out user: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/admin/users", response_model=List[UserResponse])
async def get_users(user_id: str = Depends(get_user_id_from_header)):
    """
    Get all users. Requires 'view_users' permission.
    """
    try:
        # Check if user has permission
        permission_check = supabase.rpc(
            'has_permission', 
            {'p_user_id': user_id, 'p_permission_name': 'view_users'}
        ).execute()
        
        if not permission_check.data:
            raise HTTPException(
                status_code=403,
                detail="Not enough permissions: view_users required"
            )
        
        # Get users
        result = supabase.from_("users").select("*").execute()
        return result.data
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching users: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/admin/roles", response_model=List[RoleResponse])
async def get_roles(user_id: str = Depends(get_user_id_from_header)):
    """
    Get all roles. Requires 'admin' role.
    """
    try:
        # Check if user has admin role
        roles_result = supabase.from_("user_roles") \
            .select("roles(*)") \
            .eq("user_id", user_id) \
            .execute()
            
        is_admin = any(role["roles"]["name"] == "admin" for role in roles_result.data)
        
        if not is_admin:
            raise HTTPException(
                status_code=403,
                detail="Admin role required"
            )
        
        # Get roles
        result = supabase.from_("roles").select("*").execute()
        return result.data
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching roles: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/user/me")
async def get_current_user(request: Request, user_id: str = Depends(get_user_id_from_header)):
    """
    Get current user information.
    """
    try:
        # Get user data
        user_result = supabase.from_("users").select("*").eq("id", user_id).execute()
        
        if not user_result.data:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Get user roles
        roles_result = supabase.from_("user_roles") \
            .select("roles(*)") \
            .eq("user_id", user_id) \
            .execute()
            
        roles = [role["roles"] for role in roles_result.data]
        
        # Get user permissions
        permissions = []
        for role in roles:
            perm_result = supabase.from_("role_permissions") \
                .select("permissions(*)") \
                .eq("role_id", role["id"]) \
                .execute()
                
            role_permissions = [perm["permissions"] for perm in perm_result.data]
            permissions.extend(role_permissions)
        
        # Remove duplicates
        unique_permissions = []
        perm_ids = set()
        for perm in permissions:
            if perm["id"] not in perm_ids:
                perm_ids.add(perm["id"])
                unique_permissions.append(perm)
        
        return {
            "user": user_result.data[0],
            "roles": roles,
            "permissions": unique_permissions
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching current user: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/validate-token")
async def validate_token(authorization: Optional[str] = Header(None)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Authorization header required")
    
    token = authorization.replace("Bearer ", "")
    
    # Check if token validation is cached
    cached_user_id = get_cached_token_validation(token)
    if cached_user_id:
        # Get cached user data
        cached_user = get_cached_user(cached_user_id)
        if cached_user:
            return {
                "valid": True,
                "user_id": cached_user_id,
                "user": cached_user
            }
    
    # If not cached or cache miss, verify with Supabase
    try:
        # Verify token with Supabase
        user = supabase.auth.get_user(token)
        
        # Cache validation result
        cache_token_validation(token, user.user.id)
        
        # Get or fetch user data
        cached_user = get_cached_user(user.user.id)
        if not cached_user:
            # Fetch from database and cache
            response = supabase.table("users").select("*").eq("id", user.user.id).execute()
            if response.data:
                user_data = response.data[0]
                cache_user_data(user.user.id, user_data)
            else:
                user_data = {
                    "id": user.user.id,
                    "email": user.user.email
                }
                cache_user_data(user.user.id, user_data)
        else:
            user_data = cached_user
        
        return {
            "valid": True,
            "user_id": user.user.id,
            "user": user_data
        }
    except Exception as e:
        logger.error(f"Error validating token: {e}")
        return {"valid": False, "error": str(e)}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)