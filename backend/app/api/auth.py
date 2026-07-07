import logging
import asyncio
import uuid
from datetime import datetime, timedelta, timezone
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel
from jose import jwt

from app.core.config import settings
from app.core.supabase_client import supabase
from app.core.memory_db import profiles, tickets

logger = logging.getLogger(__name__)
router = APIRouter()

class LoginRequest(BaseModel):
    role: str # 'fan', 'staff', 'admin'
    username: str

@router.post("/mock-login")
async def mock_login(request: LoginRequest) -> Dict[str, Any]:
    """
    Signs a standard HS256 JWT token representing a user with the requested role.
    This token is validated by the FastAPI JWT parser and can be used to query Supabase directly.
    """
    if request.role not in ["fan", "staff", "admin"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid role selected."
        )

    # 1. Establish deterministic UUIDs for mock profiles
    mock_uuids: Dict[str, str] = {
        "fan": "11111111-1111-1111-1111-111111111111",
        "staff": "22222222-2222-2222-2222-222222222222",
        "admin": "33333333-3333-3333-3333-333333333333"
    }
    
    user_id: str = mock_uuids.get(request.role, str(uuid.uuid4()))
    email: str = f"{request.username.lower()}@{request.role}.worldcup.org"
    full_name: str = request.username.title()
    languages: List[str] = ["en", "es"] if request.role == "staff" else ["en"]
    
    # Coordinates inside stadium (Gate C proximity for staff)
    latitude: Optional[float] = 25.9576 if request.role == "staff" else None
    longitude: Optional[float] = -80.2376 if request.role == "staff" else None

    # 2. Build standard JWT payload matching Supabase structure
    payload: Dict[str, Any] = {
        "iss": "supabase",
        "sub": user_id,
        "aud": "authenticated",
        "exp": int((datetime.now(timezone.utc) + timedelta(days=1)).timestamp()),
        "nbf": int(datetime.now(timezone.utc).timestamp()),
        "role": "authenticated",
        "email": email,
        "app_metadata": {
            "provider": "email",
            "role": request.role
        },
        "user_metadata": {
            "role": request.role,
            "full_name": full_name,
            "languages": languages,
            "latitude": latitude,
            "longitude": longitude
        }
    }

    token: str = jwt.encode(payload, settings.SUPABASE_JWT_SECRET, algorithm="HS256")

    # 3. Seed the user profile in memory DB
    profiles[user_id] = {
        "id": user_id,
        "email": email,
        "role": request.role,
        "full_name": full_name,
        "languages": languages,
        "latitude": latitude,
        "longitude": longitude,
        "is_available": True
    }
    if request.role == "fan":
        tickets[user_id] = {
            "user_id": user_id,
            "match_id": "WC-2026-M50 (USA vs ARG)",
            "seat_section": "102",
            "seat_row": "M",
            "seat_number": "14",
            "gate": "Gate C"
        }

    # 4. Attempt to seed the local Supabase container (optional)
    try:
        await asyncio.to_thread(
            lambda: supabase.table("profiles").upsert({
                "id": user_id,
                "email": email,
                "role": request.role,
                "full_name": full_name,
                "languages": languages,
                "latitude": latitude,
                "longitude": longitude,
                "is_available": True
            }).execute()
        )

        if request.role == "fan":
            await asyncio.to_thread(
                lambda: supabase.table("tickets").upsert(tickets[user_id], on_conflict="user_id").execute()
            )
    except Exception as e:
        logger.error(f"Bypassed profile auto-upsert (likely due to Supabase container offline): {e}")

    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "id": user_id,
            "email": email,
            "role": request.role,
            "full_name": full_name,
            "languages": languages
        }
    }

class SignupRequest(BaseModel):
    email: str
    password: str
    role: str # 'fan', 'staff', 'admin'
    full_name: str
    languages: Optional[List[str]] = []
    latitude: Optional[float] = None
    longitude: Optional[float] = None

class AuthLoginRequest(BaseModel):
    email: str
    password: str

@router.post("/signup")
async def signup(request: SignupRequest) -> Dict[str, Any]:
    try:
        res = await asyncio.to_thread(
            lambda: supabase.auth.sign_up({
                "email": request.email,
                "password": request.password,
                "options": {
                    "data": {
                        "role": request.role,
                        "full_name": request.full_name,
                        "languages": request.languages,
                        "latitude": request.latitude,
                        "longitude": request.longitude,
                        "is_available": True
                    }
                }
            })
        )
        
        if not res.user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Signup failed. No user object returned."
            )
            
        user_id: str = str(res.user.id)
        profiles[user_id] = {
            "id": user_id,
            "email": request.email,
            "role": request.role,
            "full_name": request.full_name,
            "languages": request.languages,
            "latitude": request.latitude,
            "longitude": request.longitude,
            "is_available": True
        }
        
        if request.role == "fan":
            tickets[user_id] = {
                "user_id": user_id,
                "match_id": "WC-2026-M50 (USA vs ARG)",
                "seat_section": "102",
                "seat_row": "M",
                "seat_number": "14",
                "gate": "Gate C"
            }
            try:
                await asyncio.to_thread(
                    lambda: supabase.table("tickets").upsert(tickets[user_id], on_conflict="user_id").execute()
                )
            except Exception as e:
                logger.error(f"Failed to upsert ticket to Supabase in signup: {e}")
                
        return {
            "status": "success",
            "user": {
                "id": user_id,
                "email": res.user.email,
                "role": request.role,
                "full_name": request.full_name
            }
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

@router.post("/login")
async def login(request: AuthLoginRequest) -> Dict[str, Any]:
    try:
        res = await asyncio.to_thread(
            lambda: supabase.auth.sign_in_with_password({
                "email": request.email,
                "password": request.password
            })
        )
        
        if not res.session:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid login credentials or session expired."
            )
            
        user = res.user
        user_metadata: Dict[str, Any] = user.user_metadata or {}
        role: str = user_metadata.get("role", "fan")
        
        user_id: str = str(user.id)
        if user_id not in profiles:
            profiles[user_id] = {
                "id": user_id,
                "email": user.email,
                "role": role,
                "full_name": user_metadata.get("full_name", "User"),
                "languages": user_metadata.get("languages", []),
                "latitude": user_metadata.get("latitude"),
                "longitude": user_metadata.get("longitude"),
                "is_available": True
            }
            
        return {
            "access_token": res.session.access_token,
            "token_type": "bearer",
            "user": {
                "id": user_id,
                "email": user.email,
                "role": role,
                "full_name": user_metadata.get("full_name", "User"),
                "languages": user_metadata.get("languages", [])
            }
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
