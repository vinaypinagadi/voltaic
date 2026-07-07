from fastapi.testclient import TestClient
from jose import jwt
from app.main import app
from app.core.config import settings
from unittest.mock import patch, MagicMock

client = TestClient(app)

def test_mock_login_fan():
    response = client.post("/api/auth/mock-login", json={"role": "fan", "username": "Vinay"})
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["user"]["role"] == "fan"
    assert data["user"]["full_name"] == "Vinay"

    payload = jwt.decode(data["access_token"], settings.SUPABASE_JWT_SECRET, algorithms=["HS256"], options={"verify_aud": False})
    assert payload["sub"] == "11111111-1111-1111-1111-111111111111"
    assert payload["email"] == "vinay@fan.worldcup.org"
    assert payload["app_metadata"]["role"] == "fan"
    assert payload["user_metadata"]["role"] == "fan"

def test_mock_login_staff():
    response = client.post("/api/auth/mock-login", json={"role": "staff", "username": "Staffy"})
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["user"]["role"] == "staff"

def test_mock_login_exception(mock_supabase):
    def side_effect(table_name):
        raise Exception("DB Error")
    mock_supabase["client"].table.side_effect = side_effect
    response = client.post("/api/auth/mock-login", json={"role": "fan", "username": "Vinay"})
    assert response.status_code == 200

def test_signup_ticket_upsert_exception(mock_supabase):
    mock_supabase_auth = MagicMock()
    mock_user = MagicMock()
    mock_user.id = "signup-ticket-uuid"
    mock_user.email = "ticket@example.com"
    mock_res = MagicMock()
    mock_res.user = mock_user
    mock_supabase_auth.sign_up.return_value = mock_res
    
    with patch("app.api.auth.supabase.auth", new=mock_supabase_auth):
        def side_effect(table_name):
            if table_name == "tickets":
                raise Exception("Upsert Error")
            return MagicMock()
        mock_supabase["client"].table.side_effect = side_effect
        response = client.post("/api/auth/signup", json={
            "email": "ticket@example.com",
            "password": "pass",
            "role": "fan",
            "full_name": "Test Fan"
        })
        assert response.status_code == 200

def test_mock_login_invalid_role():
    response = client.post("/api/auth/mock-login", json={"role": "guest", "username": "Vinay"})
    assert response.status_code == 400
    assert "Invalid role" in response.json()["detail"]

def test_signup_success(mock_supabase):
    mock_supabase_auth = MagicMock()
    mock_user = MagicMock()
    mock_user.id = "new-uuid"
    mock_user.email = "test@example.com"
    mock_res = MagicMock()
    mock_res.user = mock_user
    mock_supabase_auth.sign_up.return_value = mock_res
    
    with patch("app.api.auth.supabase.auth", new=mock_supabase_auth):
        response = client.post("/api/auth/signup", json={
            "email": "test@example.com",
            "password": "pass",
            "role": "fan",
            "full_name": "Test Fan"
        })
        assert response.status_code == 200
        assert response.json()["user"]["email"] == "test@example.com"

def test_signup_no_user(mock_supabase):
    mock_supabase_auth = MagicMock()
    mock_res = MagicMock()
    mock_res.user = None
    mock_supabase_auth.sign_up.return_value = mock_res
    
    with patch("app.api.auth.supabase.auth", new=mock_supabase_auth):
        response = client.post("/api/auth/signup", json={
            "email": "test@example.com",
            "password": "pass",
            "role": "fan",
            "full_name": "Test Fan"
        })
        assert response.status_code == 400
        assert "No user object" in response.json()["detail"]

def test_signup_exception():
    with patch("app.api.auth.supabase.auth.sign_up", side_effect=Exception("DB Error")):
        response = client.post("/api/auth/signup", json={
            "email": "test@example.com",
            "password": "pass",
            "role": "fan",
            "full_name": "Test Fan"
        })
        assert response.status_code == 400
        assert "DB Error" in response.json()["detail"]

def test_login_success(mock_supabase):
    mock_supabase_auth = MagicMock()
    mock_user = MagicMock()
    mock_user.id = "login-uuid"
    mock_user.email = "test@example.com"
    mock_user.user_metadata = {"role": "fan", "full_name": "Test Fan"}
    
    mock_session = MagicMock()
    mock_session.access_token = "mock_token"
    
    mock_res = MagicMock()
    mock_res.user = mock_user
    mock_res.session = mock_session
    mock_supabase_auth.sign_in_with_password.return_value = mock_res
    
    with patch("app.api.auth.supabase.auth", new=mock_supabase_auth):
        response = client.post("/api/auth/login", json={
            "email": "test@example.com",
            "password": "pass"
        })
        assert response.status_code == 200
        assert response.json()["access_token"] == "mock_token"

def test_login_no_session(mock_supabase):
    mock_supabase_auth = MagicMock()
    mock_res = MagicMock()
    mock_res.session = None
    mock_supabase_auth.sign_in_with_password.return_value = mock_res
    
    with patch("app.api.auth.supabase.auth", new=mock_supabase_auth):
        response = client.post("/api/auth/login", json={
            "email": "test@example.com",
            "password": "pass"
        })
        assert response.status_code == 400
        assert "Invalid login" in response.json()["detail"]

def test_login_exception():
    with patch("app.api.auth.supabase.auth.sign_in_with_password", side_effect=Exception("DB Error")):
        response = client.post("/api/auth/login", json={
            "email": "test@example.com",
            "password": "pass"
        })
        assert response.status_code == 400
        assert "DB Error" in response.json()["detail"]
