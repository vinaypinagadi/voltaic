from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock, MagicMock
from app.main import app

client = TestClient(app)

def test_chat_streaming_unauthorized():
    response = client.post(
        "/api/chat/stream",
        json={"message": "Hello", "history": []}
    )
    assert response.status_code == 401

def test_chat_streaming_normal():
    login_res = client.post("/api/auth/mock-login", json={"role": "fan", "username": "Vinay"})
    token = login_res.json()["access_token"]

    headers = {"Authorization": f"Bearer {token}"}
    response = client.post(
        "/api/chat/stream",
        json={"message": "Where is my seat in section 102?", "history": []},
        headers=headers
    )
    assert response.status_code == 200
    assert response.headers["content-type"] == "text/plain; charset=utf-8"
    
    content = response.text
    assert len(content) > 0

def test_chat_streaming_emergency():
    login_res = client.post("/api/auth/mock-login", json={"role": "fan", "username": "Vinay"})
    token = login_res.json()["access_token"]

    headers = {"Authorization": f"Bearer {token}"}
    response = client.post(
        "/api/chat/stream",
        json={"message": "Help me, I am having chest pain near section 100", "history": []},
        headers=headers
    )
    assert response.status_code == 200
    content = response.text
    assert "EMERGENCY PROTOCOL TRIGGERED" in content

def test_chat_streaming_emergency_exceptions(mock_supabase):
    login_res = client.post("/api/auth/mock-login", json={"role": "fan", "username": "Vinay"})
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    
    with patch("app.api.chat.asyncio.to_thread", new_callable=AsyncMock) as mock_thread:
        mock_thread.side_effect = Exception("DB Error")
        response = client.post("/api/chat/stream", json={"message": "Help me, medical emergency!", "history": []}, headers=headers)
        assert response.status_code == 200
        assert "EMERGENCY PROTOCOL TRIGGERED" in response.text

def test_chat_streaming_normal_exceptions(mock_supabase):
    login_res = client.post("/api/auth/mock-login", json={"role": "fan", "username": "Vinay"})
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    
    with patch("app.api.chat.asyncio.to_thread", new_callable=AsyncMock) as mock_thread:
        mock_thread.side_effect = Exception("DB Error")
        response = client.post("/api/chat/stream", json={"message": "Where is Gate A?", "history": []}, headers=headers)
        assert response.status_code == 200

def test_chat_streaming_emergency_with_ticket(mock_supabase):
    login_res = client.post("/api/auth/mock-login", json={"role": "fan", "username": "Vinay"})
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    
    with patch("app.api.chat.asyncio.to_thread", new_callable=AsyncMock) as mock_thread:
        mock_res = MagicMock()
        mock_res.data = [{"seat_section": "102", "seat_row": "A", "seat_number": "1", "gate": "A"}]
        mock_thread.return_value = mock_res
        response = client.post("/api/chat/stream", json={"message": "Help me, medical emergency!", "history": []}, headers=headers)
        assert response.status_code == 200
