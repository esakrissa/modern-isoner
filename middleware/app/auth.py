from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import jwt
from supabase import create_client
import os
import redis
import json
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Get environment variables
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
REDIS_PASSWORD = os.getenv("REDIS_PASSWORD", "")
JWT_SECRET = os.getenv("JWT_SECRET", "your-secret-key")  # In production, use a secure secret key

# Initialize components
security = HTTPBearer()
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# Initialize Redis client
try:
    redis_client = redis.Redis(
        host=REDIS_HOST,
        port=REDIS_PORT,
        password=REDIS_PASSWORD,
        decode_responses=True
    )
except Exception as e:
    logger.warning(f"Redis connection failed: {e}. Caching will be disabled.")
    redis_client = None

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """
    Extracts and validates the user ID from the JWT token in the Authorization header.
    
    Args:
        credentials: The credentials extracted from the Authorization header
        
    Returns:
        str: The user ID if the token is valid
        
    Raises:
        HTTPException: If the token is invalid or missing
    """
    try:
        # In production, use proper verification
        # payload = jwt.decode(credentials.credentials, JWT_SECRET, algorithms=["HS256"])
        
        # For development/testing
        payload = jwt.decode(credentials.credentials, options={"verify_signature": False})
        user_id = payload.get("sub")
        
        if user_id is None:
            logger.warning("Token missing 'sub' claim")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, 
                detail="Invalid token: missing user ID"
            )
            
        logger.info(f"Authenticated user: {user_id}")
        return user_id
    except jwt.PyJWTError as e:
        logger.error(f"JWT decode error: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, 
            detail=f"Invalid token: {str(e)}"
        )

def has_permission(permission: str):
    """
    Factory function that creates a dependency to check if a user has a specific permission.
    
    Args:
        permission: The permission to check for
        
    Returns:
        function: A dependency function that checks the permission
    """
    def permission_checker(user_id: str = Depends(get_current_user)):
        logger.info(f"Checking permission '{permission}' for user {user_id}")
        
        # Try to get from cache first
        if redis_client:
            cache_key = f"perm:{user_id}:{permission}"
            cached_result = redis_client.get(cache_key)
            
            if cached_result:
                logger.info(f"Permission check cache hit for {user_id}:{permission}")
                has_perm = cached_result == "1"
                if not has_perm:
                    logger.warning(f"Permission denied (from cache): {user_id} lacks {permission}")
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail=f"Not enough permissions: {permission} required"
                    )
                return user_id
        
        # Check permission in Supabase
        try:
            result = supabase.rpc(
                'has_permission', 
                {'p_user_id': user_id, 'p_permission_name': permission}
            ).execute()
            
            has_perm = bool(result.data)
            
            # Cache result if Redis is available
            if redis_client:
                redis_client.setex(
                    f"perm:{user_id}:{permission}", 
                    300,  # Cache for 5 minutes
                    "1" if has_perm else "0"
                )
            
            if not has_perm:
                logger.warning(f"Permission denied: {user_id} lacks {permission}")
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Not enough permissions: {permission} required"
                )
                
            logger.info(f"Permission granted: {user_id} has {permission}")
            return user_id
        except Exception as e:
            logger.error(f"Error checking permission: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error checking permissions: {str(e)}"
            )
            
    return permission_checker

class RoleBasedAccessControl:
    """
    Class for role-based access control functionality.
    Provides methods to check roles and manage permissions.
    """
    
    @staticmethod
    async def get_user_roles(user_id: str):
        """
        Get all roles assigned to a user.
        
        Args:
            user_id: The user ID to check roles for
            
        Returns:
            list: List of role objects
        """
        try:
            # Try to get from cache first
            if redis_client:
                cache_key = f"roles:{user_id}"
                cached_result = redis_client.get(cache_key)
                
                if cached_result:
                    return json.loads(cached_result)
            
            # Get roles from Supabase
            result = supabase.from_("user_roles") \
                .select("roles(*)") \
                .eq("user_id", user_id) \
                .execute()
                
            roles = [role["roles"] for role in result.data]
            
            # Cache result if Redis is available
            if redis_client:
                redis_client.setex(
                    f"roles:{user_id}", 
                    300,  # Cache for 5 minutes
                    json.dumps(roles)
                )
                
            return roles
        except Exception as e:
            logger.error(f"Error getting user roles: {e}")
            return []
    
    @staticmethod
    async def has_role(user_id: str, role_name: str):
        """
        Check if a user has a specific role.
        
        Args:
            user_id: The user ID to check
            role_name: The role name to check for
            
        Returns:
            bool: True if the user has the role, False otherwise
        """
        roles = await RoleBasedAccessControl.get_user_roles(user_id)
        return any(role["name"] == role_name for role in roles)
    
    @staticmethod
    def role_required(role_name: str):
        """
        Factory function that creates a dependency to check if a user has a specific role.
        
        Args:
            role_name: The role to check for
            
        Returns:
            function: A dependency function that checks the role
        """
        async def role_checker(user_id: str = Depends(get_current_user)):
            if not await RoleBasedAccessControl.has_role(user_id, role_name):
                logger.warning(f"Role check failed: {user_id} is not a {role_name}")
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Role '{role_name}' required"
                )
            return user_id
        return role_checker 