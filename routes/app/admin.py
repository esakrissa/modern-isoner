from fastapi import APIRouter, Depends, HTTPException, status
from middleware.app.auth import has_permission, RoleBasedAccessControl
from supabase import create_client
import os
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Supabase setup
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

router = APIRouter(prefix="/admin", tags=["admin"])

@router.get("/users", dependencies=[Depends(has_permission("view_users"))])
async def get_users():
    """
    Get all users. Requires 'view_users' permission.
    """
    try:
        result = supabase.from_("users").select("*").execute()
        return {"users": result.data}
    except Exception as e:
        logger.error(f"Error fetching users: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching users: {str(e)}"
        )

@router.get("/roles", dependencies=[Depends(RoleBasedAccessControl.role_required("admin"))])
async def get_roles():
    """
    Get all roles. Requires 'admin' role.
    """
    try:
        result = supabase.from_("roles").select("*").execute()
        return {"roles": result.data}
    except Exception as e:
        logger.error(f"Error fetching roles: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching roles: {str(e)}"
        )

@router.get("/permissions", dependencies=[Depends(has_permission("manage_permissions"))])
async def get_permissions():
    """
    Get all permissions. Requires 'manage_permissions' permission.
    """
    try:
        result = supabase.from_("permissions").select("*").execute()
        return {"permissions": result.data}
    except Exception as e:
        logger.error(f"Error fetching permissions: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching permissions: {str(e)}"
        )

@router.post("/assign-role", dependencies=[Depends(has_permission("assign_roles"))])
async def assign_role(user_id: str, role_id: str):
    """
    Assign a role to a user. Requires 'assign_roles' permission.
    """
    try:
        # Check if user exists
        user_result = supabase.from_("users").select("id").eq("id", user_id).execute()
        if not user_result.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User with ID {user_id} not found"
            )
            
        # Check if role exists
        role_result = supabase.from_("roles").select("id").eq("id", role_id).execute()
        if not role_result.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Role with ID {role_id} not found"
            )
            
        # Assign role to user
        result = supabase.from_("user_roles").insert({
            "user_id": user_id,
            "role_id": role_id
        }).execute()
        
        return {"message": "Role assigned successfully", "data": result.data}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error assigning role: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error assigning role: {str(e)}"
        )

@router.delete("/revoke-role", dependencies=[Depends(has_permission("assign_roles"))])
async def revoke_role(user_id: str, role_id: str):
    """
    Revoke a role from a user. Requires 'assign_roles' permission.
    """
    try:
        result = supabase.from_("user_roles") \
            .delete() \
            .eq("user_id", user_id) \
            .eq("role_id", role_id) \
            .execute()
            
        if not result.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Role assignment not found"
            )
            
        return {"message": "Role revoked successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error revoking role: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error revoking role: {str(e)}"
        )

@router.post("/assign-permission", dependencies=[Depends(has_permission("manage_permissions"))])
async def assign_permission(role_id: str, permission_id: str):
    """
    Assign a permission to a role. Requires 'manage_permissions' permission.
    """
    try:
        # Check if role exists
        role_result = supabase.from_("roles").select("id").eq("id", role_id).execute()
        if not role_result.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Role with ID {role_id} not found"
            )
            
        # Check if permission exists
        perm_result = supabase.from_("permissions").select("id").eq("id", permission_id).execute()
        if not perm_result.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Permission with ID {permission_id} not found"
            )
            
        # Assign permission to role
        result = supabase.from_("role_permissions").insert({
            "role_id": role_id,
            "permission_id": permission_id
        }).execute()
        
        return {"message": "Permission assigned successfully", "data": result.data}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error assigning permission: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error assigning permission: {str(e)}"
        )

@router.delete("/revoke-permission", dependencies=[Depends(has_permission("manage_permissions"))])
async def revoke_permission(role_id: str, permission_id: str):
    """
    Revoke a permission from a role. Requires 'manage_permissions' permission.
    """
    try:
        result = supabase.from_("role_permissions") \
            .delete() \
            .eq("role_id", role_id) \
            .eq("permission_id", permission_id) \
            .execute()
            
        if not result.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Permission assignment not found"
            )
            
        return {"message": "Permission revoked successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error revoking permission: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error revoking permission: {str(e)}"
        )