from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_chat_streaming_unauthorized():
    # Call without Authorization header
    response = client.post(
        "/api/chat/stream",
        json={"message": "Hello", "history": []}
    )
    assert response.status_code == 401  # HTTPBearer returns 401 when header is missing

def test_chat_streaming_normal():
    # 1. Sign in to obtain a valid token
    login_res = client.post("/api/auth/mock-login", json={"role": "fan", "username": "Vinay"})
    token = login_res.json()["access_token"]

    # 2. Request chat stream using token
    headers = {"Authorization": f"Bearer {token}"}
    response = client.post(
        "/api/chat/stream",
        json={"message": "Where is my seat in section 102?", "history": []},
        headers=headers
    )
    assert response.status_code == 200
    assert response.headers["content-type"] == "text/plain; charset=utf-8"
    
    # Read streamed body
    content = response.text
    assert len(content) > 0
    assert "[MOCK STREAM]" in content or len(content) > 0

def test_chat_streaming_emergency():
    # 1. Sign in
    login_res = client.post("/api/auth/mock-login", json={"role": "fan", "username": "Vinay"})
    token = login_res.json()["access_token"]

    # 2. Request chat stream with emergency trigger
    headers = {"Authorization": f"Bearer {token}"}
    response = client.post(
        "/api/chat/stream",
        json={"message": "Help me, I am having chest pain near section 100", "history": []},
        headers=headers
    )
    assert response.status_code == 200
    content = response.text
    # Deterministic emergency fallback should activate immediately
    assert "EMERGENCY PROTOCOL TRIGGERED" in content
