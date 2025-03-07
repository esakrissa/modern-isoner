from fastapi import Request, HTTPException, status
from fastapi.middleware.base import BaseHTTPMiddleware
import jwt
import os
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Get environment variables
JWT_SECRET = os.getenv("JWT_SECRET", "your-secret-key")  # In production, use a secure secret key

class AuthMiddleware(BaseHTTPMiddleware):
    """
    Middleware for authentication.
    Validates JWT tokens in the Authorization header.
    """
    
    async def dispatch(self, request: Request, call_next):
        """
        Process the request and validate JWT token if required.
        
        Args:
            request: The incoming request
            call_next: The next middleware or endpoint handler
            
        Returns:
            Response: The response from the next middleware or endpoint
        """
        # Exclude paths that don't require authentication
        excluded_paths = [
            "/health",
            "/docs",
            "/openapi.json",
            "/api/v1/auth/login",
            "/api/v1/auth/register"
        ]
        
        # Check if path is excluded
        if any(request.url.path.startswith(path) for path in excluded_paths):
            logger.info(f"Skipping auth for excluded path: {request.url.path}")
            return await call_next(request)
        
        # Check for Authorization header
        auth_header = request.headers.get("Authorization")
        if not auth_header:
            logger.warning(f"Missing Authorization header: {request.url.path}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authorization header missing"
            )
        
        # Extract token
        try:
            scheme, token = auth_header.split()
            if scheme.lower() != "bearer":
                logger.warning(f"Invalid auth scheme: {scheme}")
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid authentication scheme"
                )
        except ValueError:
            logger.warning(f"Invalid Authorization header format")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid Authorization header format"
            )
        
        # Validate token
        try:
            # In production, use proper verification
            # payload = jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
            
            # For development/testing
            payload = jwt.decode(token, options={"verify_signature": False})
            
            # Check if token has user ID
            if "sub" not in payload:
                logger.warning(f"Token missing 'sub' claim")
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid token: missing user ID"
                )
            
            # Add user ID to request state
            request.state.user_id = payload["sub"]
            logger.info(f"Authenticated user: {payload['sub']} for {request.url.path}")
            
            # Process the request
            return await call_next(request)
        except jwt.PyJWTError as e:
            logger.error(f"JWT validation error: {e}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Invalid token: {str(e)}"
            )
        except Exception as e:
            logger.error(f"Unexpected error in auth middleware: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Internal server error"
            ) 