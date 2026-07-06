from fastapi.testclient import TestClient
from jose import jwt
from app.main import app
from app.core.config import settings

client = TestClient(app)

def test_mock_login_fan():
    response = client.post("/api/auth/mock-login", json={"role": "fan", "username": "Vinay"})
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["user"]["role"] == "fan"
    assert data["user"]["full_name"] == "Vinay"

    # Decode and verify the JWT payload
    payload = jwt.decode(data["access_token"], settings.SUPABASE_JWT_SECRET, algorithms=["HS256"], options={"verify_aud": False})
    assert payload["sub"] == "11111111-1111-1111-1111-111111111111"
    assert payload["email"] == "vinay@fan.worldcup.org"
    assert payload["app_metadata"]["role"] == "fan"
    assert payload["user_metadata"]["role"] == "fan"

def test_mock_login_invalid_role():
    response = client.post("/api/auth/mock-login", json={"role": "guest", "username": "Vinay"})
    assert response.status_code == 400
    assert "Invalid role" in response.json()["detail"]
