from fastapi.testclient import TestClient
from unittest.mock import MagicMock, patch, AsyncMock
from app.main import app
from app.core.supabase_client import supabase

client = TestClient(app)

def test_dispatch_suggestions_unauthorized():
    response = client.get("/api/dispatch/suggestions/alert-123")
    assert response.status_code == 401

def test_dispatch_suggestions_low_clearance():
    login_res = client.post("/api/auth/mock-login", json={"role": "fan", "username": "Vinay"})
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    response = client.get("/api/dispatch/suggestions/alert-123", headers=headers)
    assert response.status_code == 403

def test_dispatch_suggestions_staff(mock_supabase):
    login_res = client.post("/api/auth/mock-login", json={"role": "staff", "username": "Volunteer"})
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    mock_execute_alert = MagicMock()
    mock_execute_alert.data = [{
        "id": "alert-123",
        "title": "🚨 EMERGENCY: MEDICAL - Fan",
        "description": "Fan experiencing chest pain near Gate A",
        "category": "medical",
        "status": "pending",
        "location": "Gate A",
        "severity": "critical"
    }]
    mock_execute_alert.error = None

    mock_execute_staff = MagicMock()
    mock_execute_staff.data = [
        {
            "id": "volunteer-en",
            "full_name": "English Speaker",
            "email": "en@staff.worldcup.org",
            "role": "staff",
            "languages": ["en"],
            "latitude": 25.9586,
            "longitude": -80.2394,
            "is_available": True
        }
    ]
    mock_execute_staff.error = None

    def side_effect(table_name):
        mock_table = MagicMock()
        if table_name == "staff_alerts":
            mock_select = MagicMock()
            mock_table.select.return_value = mock_select
            mock_eq = MagicMock()
            mock_select.eq.return_value = mock_eq
            mock_eq.execute.return_value = mock_execute_alert
            return mock_table
        elif table_name == "profiles":
            mock_select = MagicMock()
            mock_table.select.return_value = mock_select
            mock_eq = MagicMock()
            mock_select.eq.return_value = mock_eq
            mock_eq2 = MagicMock()
            mock_eq.eq.return_value = mock_eq2
            mock_eq2.execute.return_value = mock_execute_staff
            return mock_table
        return mock_table

    mock_supabase["client"].table.side_effect = side_effect

    response = client.get("/api/dispatch/suggestions/alert-123", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["alert"]["id"] == "alert-123"
    assert len(data["suggestions"]) > 0
    assert data["suggestions"][0]["full_name"] == "English Speaker"

def test_dispatch_suggestions_not_found(mock_supabase):
    login_res = client.post("/api/auth/mock-login", json={"role": "staff", "username": "Volunteer"})
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    mock_execute_alert = MagicMock()
    mock_execute_alert.data = []  # No alert found
    mock_execute_alert.error = None

    def side_effect(table_name):
        mock_table = MagicMock()
        if table_name == "staff_alerts":
            mock_select = MagicMock()
            mock_table.select.return_value = mock_select
            mock_eq = MagicMock()
            mock_select.eq.return_value = mock_eq
            mock_eq.execute.return_value = mock_execute_alert
            return mock_table
        return mock_table

    mock_supabase["client"].table.side_effect = side_effect
    
    with patch("app.api.dispatch.memory_db.staff_alerts", []):
        response = client.get("/api/dispatch/suggestions/alert-not-exist", headers=headers)
        assert response.status_code == 404

def test_list_alerts_staff(mock_supabase):
    login_res = client.post("/api/auth/mock-login", json={"role": "staff", "username": "Volunteer"})
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    mock_execute = MagicMock()
    mock_execute.data = [{"id": "alert-1"}]
    mock_order = MagicMock()
    mock_order.execute.return_value = mock_execute
    mock_select = MagicMock()
    mock_select.order.return_value = mock_order
    mock_table = MagicMock()
    mock_table.select.return_value = mock_select
    mock_supabase["client"].table.return_value = mock_table
    
    response = client.get("/api/dispatch/alerts", headers=headers)
    assert response.status_code == 200
    assert len(response.json()) > 0

def test_assign_dispatch_success(mock_supabase):
    login_res = client.post("/api/auth/mock-login", json={"role": "staff", "username": "Volunteer"})
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    
    with patch("app.api.dispatch.memory_db.staff_alerts", [{"id": "mock-alert-1", "status": "pending"}]):
        response = client.post("/api/dispatch/assign", json={
            "alert_id": "mock-alert-1",
            "staff_id": "staff-123"
        }, headers=headers)
        assert response.status_code == 200
        assert "successfully dispatched" in response.json()["message"]

def test_assign_dispatch_not_found(mock_supabase):
    login_res = client.post("/api/auth/mock-login", json={"role": "staff", "username": "Volunteer"})
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    
    with patch("app.api.dispatch.asyncio.to_thread", new_callable=AsyncMock) as mock_thread:
        mock_thread.side_effect = Exception("DB Error")

        with patch("app.api.dispatch.memory_db.staff_alerts", []):
            response = client.post("/api/dispatch/assign", json={
                "alert_id": "not-found",
                "staff_id": "staff-123"
            }, headers=headers)
            assert response.status_code == 404

def test_get_location_coordinates_unknown():
    from app.api.dispatch import get_location_coordinates
    assert get_location_coordinates("nowhere") == (25.9580, -80.2389)

def test_detect_incident_language_all():
    from app.api.dispatch import detect_incident_language
    assert detect_incident_language("medico emergency") == "es"
    assert detect_incident_language("مرحبا") == "ar"
    assert detect_incident_language("こんにちは") == "ja"
    assert detect_incident_language("привет") == "ru"
    assert detect_incident_language("hello") == "en"

def test_list_alerts_exception(mock_supabase):
    login_res = client.post("/api/auth/mock-login", json={"role": "staff", "username": "Volunteer"})
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    
    with patch("app.api.dispatch.asyncio.to_thread", new_callable=AsyncMock) as mock_thread:
        mock_thread.side_effect = Exception("DB Error")
        response = client.get("/api/dispatch/alerts", headers=headers)
        assert response.status_code == 200

def test_get_dispatch_suggestions_exceptions(mock_supabase):
    login_res = client.post("/api/auth/mock-login", json={"role": "staff", "username": "Volunteer"})
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    
    with patch("app.api.dispatch.asyncio.to_thread", new_callable=AsyncMock) as mock_thread:
        mock_thread.side_effect = Exception("DB Error")
        
        with patch("app.api.dispatch.memory_db.staff_alerts", [{"id": "mock-alert-1", "location": "gate a"}]):
            response = client.get("/api/dispatch/suggestions/mock-alert-1", headers=headers)
            assert response.status_code == 200

def test_list_alerts_with_db_data(mock_supabase):
    login_res = client.post("/api/auth/mock-login", json={"role": "staff", "username": "Volunteer"})
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    
    from unittest.mock import AsyncMock
    with patch("app.api.dispatch.asyncio.to_thread", new_callable=AsyncMock) as mock_thread:
        mock_res = MagicMock()
        mock_res.data = [{"id": "alert-1", "created_at": "2024-01-01"}]
        mock_thread.return_value = mock_res
        response = client.get("/api/dispatch/alerts", headers=headers)
        assert response.status_code == 200
        assert len(response.json()) > 0
