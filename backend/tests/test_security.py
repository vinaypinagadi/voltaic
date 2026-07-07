import pytest
import asyncio
from unittest.mock import MagicMock, patch, AsyncMock
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials
from app.core.security import get_current_user, require_staff_or_admin
from jose import jwt
from app.core.config import settings

@pytest.fixture
def valid_token_fan():
    payload = {
        "sub": "user-123",
        "email": "fan@example.com",
        "app_metadata": {"role": "fan"},
        "user_metadata": {"full_name": "Fan User"}
    }
    return jwt.encode(payload, settings.SUPABASE_JWT_SECRET, algorithm="HS256")

@pytest.fixture
def valid_token_staff():
    payload = {
        "sub": "staff-123",
        "email": "staff@example.com",
        "app_metadata": {"role": "staff"},
        "user_metadata": {"full_name": "Staff User"}
    }
    return jwt.encode(payload, settings.SUPABASE_JWT_SECRET, algorithm="HS256")

@pytest.fixture
def invalid_token_missing_sub():
    payload = {
        "email": "fan@example.com"
    }
    return jwt.encode(payload, settings.SUPABASE_JWT_SECRET, algorithm="HS256")

@pytest.mark.asyncio
async def test_get_current_user_local_fallback_success(valid_token_fan):
    creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials=valid_token_fan)
    user = await get_current_user(creds)
    assert user["id"] == "user-123"
    assert user["role"] == "fan"
    assert user["email"] == "fan@example.com"

@pytest.mark.asyncio
async def test_get_current_user_missing_sub(invalid_token_missing_sub):
    creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials=invalid_token_missing_sub)
    with pytest.raises(HTTPException) as exc:
        await get_current_user(creds)
    assert exc.value.status_code == 401
    assert "missing sub" in exc.value.detail

@pytest.mark.asyncio
async def test_get_current_user_invalid_jwt():
    creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials="invalid-token")
    with pytest.raises(HTTPException) as exc:
        await get_current_user(creds)
    assert exc.value.status_code == 401
    assert "Invalid authentication credentials" in exc.value.detail

@pytest.mark.asyncio
async def test_get_current_user_supabase_auth_success():
    creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials="fake_token")
    
    class MockAuthClient:
        pass
        
    mock_supabase_auth = MockAuthClient()
    mock_user = MagicMock()
    mock_user.id = "user-abc"
    mock_user.email = "live@example.com"
    mock_user.user_metadata = {"role": "admin", "full_name": "Live Admin"}
    
    mock_response = MagicMock()
    mock_response.user = mock_user
    
    mock_supabase_auth.get_user = MagicMock(return_value=mock_response)
    
    with patch("app.core.security.supabase.auth", mock_supabase_auth):
        user = await get_current_user(creds)
        assert user["id"] == "user-abc"
        assert user["role"] == "admin"

@pytest.mark.asyncio
async def test_require_staff_or_admin_fan():
    user = {"role": "fan"}
    with pytest.raises(HTTPException) as exc:
        require_staff_or_admin(user)
    assert exc.value.status_code == 403

def test_require_staff_or_admin_staff():
    user = {"role": "staff"}
    result = require_staff_or_admin(user)
    assert result == user

def test_require_staff_or_admin_admin():
    user = {"role": "admin"}
    result = require_staff_or_admin(user)
    assert result == user

@pytest.mark.asyncio
async def test_get_current_user_supabase_auth_exception():
    creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials="fake_token")
    
    class MockAuthClient:
        pass
        
    mock_supabase_auth = MockAuthClient()
    mock_supabase_auth.get_user = MagicMock(side_effect=Exception("Auth DB Error"))
    
    with patch("app.core.security.supabase.auth", mock_supabase_auth):
        with pytest.raises(HTTPException):
            await get_current_user(creds)
