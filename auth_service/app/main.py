from fastapi import FastAPI, HTTPException, Depends, Header, Request
from pydantic import BaseModel
from supabase import create_client, Client
import os
from typing import Optional, List
import logging
import jwt

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
async def logout():
    try:
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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)