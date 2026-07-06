from fastapi.testclient import TestClient
from unittest.mock import MagicMock
from app.main import app
from app.core.supabase_client import supabase

client = TestClient(app)

def test_dispatch_suggestions_unauthorized():
    response = client.get("/api/dispatch/suggestions/alert-123")
    assert response.status_code == 401

def test_dispatch_suggestions_low_clearance():
    # Fan login
    login_res = client.post("/api/auth/mock-login", json={"role": "fan", "username": "Vinay"})
    token = login_res.json()["access_token"]
    
    headers = {"Authorization": f"Bearer {token}"}
    response = client.get("/api/dispatch/suggestions/alert-123", headers=headers)
    assert response.status_code == 403

def test_dispatch_suggestions_staff(mock_supabase):
    # 1. Staff login
    login_res = client.post("/api/auth/mock-login", json={"role": "staff", "username": "Volunteer"})
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 2. Mock supabase responses for alert and staff profiles
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
            "latitude": 25.9586,  # Very close to Gate A (25.9585, -80.2395)
            "longitude": -80.2394,
            "is_available": True
        },
        {
            "id": "volunteer-es",
            "full_name": "Spanish Speaker",
            "email": "es@staff.worldcup.org",
            "role": "staff",
            "languages": ["es"],
            "latitude": 25.9570,  # Further away
            "longitude": -80.2370,
            "is_available": True
        }
    ]
    mock_execute_staff.error = None

    # Side-effect mocking for table selections
    # First call: select alert
    # Second call: select staff profiles
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

    # 3. Call dispatch suggestions
    response = client.get("/api/dispatch/suggestions/alert-123", headers=headers)
    assert response.status_code == 200
    data = response.json()
    
    assert data["alert"]["id"] == "alert-123"
    assert len(data["suggestions"]) > 0
    # English Speaker volunteer should rank higher because they are extremely close (few meters away)
    assert data["suggestions"][0]["full_name"] == "English Speaker"
    assert data["suggestions"][0]["distance_meters"] < 50.0  # Should be very close
