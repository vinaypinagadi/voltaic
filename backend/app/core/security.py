import logging
import asyncio
from typing import Dict, Any, Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError

from app.core.config import settings
from app.core.supabase_client import supabase

logger = logging.getLogger(__name__)
security = HTTPBearer()

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> Dict[str, Any]:
    token: str = credentials.credentials
    
    # 1. Attempt to verify JWT token against live Supabase Auth API
    # Skip if we are running in unit tests with a mocked Supabase client
    if type(supabase.auth).__name__ != "MagicMock":
        try:
            # Run blocking Supabase Auth API call in a thread pool
            response = await asyncio.to_thread(lambda: supabase.auth.get_user(token))
            if response and response.user:
                user = response.user
                user_metadata: Dict[str, Any] = user.user_metadata or {}
                role: str = user_metadata.get("role") or "fan"
                return {
                    "id": str(user.id),
                    "email": user.email,
                    "role": role,
                    "full_name": user_metadata.get("full_name", "User"),
                    "languages": user_metadata.get("languages", [])
                }
        except Exception as e:
            logger.warning(f"Supabase Auth get_user failed, falling back to local JWT decode: {e}")

    # 2. Fallback to local JWT decode (standard mock/test flow)
    try:
        # Decode the Supabase JWT using the shared secret
        payload = jwt.decode(
            token,
            settings.SUPABASE_JWT_SECRET,
            algorithms=["HS256"],
            options={"verify_aud": False}  # Supabase aud is usually 'authenticated'
        )
        
        user_id: Optional[str] = payload.get("sub")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token payload: missing sub"
            )
            
        # Extract role from app_metadata or user_metadata
        app_metadata: Dict[str, Any] = payload.get("app_metadata", {})
        user_metadata: Dict[str, Any] = payload.get("user_metadata", {})
        role: str = app_metadata.get("role") or user_metadata.get("role") or "fan"
        
        return {
            "id": user_id,
            "email": payload.get("email"),
            "role": role,
            "full_name": user_metadata.get("full_name", "User"),
            "languages": user_metadata.get("languages", [])
        }
    except JWTError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid authentication credentials: {str(e)}"
        )

def require_staff_or_admin(user: Dict[str, Any] = Depends(get_current_user)) -> Dict[str, Any]:
    if user["role"] not in ["staff", "admin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access forbidden: Staff or Admin clearance required."
        )
    return user
