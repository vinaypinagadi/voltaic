from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_record_telemetry_unauthorized():
    # Calling telemetry endpoint without credentials
    payload = {
        "gate_name": "Gate B",
        "entry_rate": 150.0,
        "queue_wait_time": 20.0,
        "crowd_density": "critical"
    }
    response = client.post("/api/telemetry", json=payload)
    assert response.status_code == 401

def test_record_telemetry_low_clearance_fan():
    # 1. Sign in as a fan
    login_res = client.post("/api/auth/mock-login", json={"role": "fan", "username": "Vinay"})
    token = login_res.json()["access_token"]

    # 2. Try to post telemetry
    headers = {"Authorization": f"Bearer {token}"}
    payload = {
        "gate_name": "Gate B",
        "entry_rate": 150.0,
        "queue_wait_time": 20.0,
        "crowd_density": "critical"
    }
    response = client.post("/api/telemetry", json=payload, headers=headers)
    assert response.status_code == 403
    assert "Staff or Admin clearance required" in response.json()["detail"]

def test_record_telemetry_authorized_staff():
    # 1. Sign in as staff
    login_res = client.post("/api/auth/mock-login", json={"role": "staff", "username": "Volunteer"})
    token = login_res.json()["access_token"]

    # 2. Post normal telemetry (no bottleneck)
    headers = {"Authorization": f"Bearer {token}"}
    payload = {
        "gate_name": "Gate A",
        "entry_rate": 60.0,
        "queue_wait_time": 5.0,
        "crowd_density": "low"
    }
    response = client.post("/api/telemetry", json=payload, headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["bottleneck_detected"] is False

def test_record_telemetry_bottleneck_critical():
    # 1. Sign in as admin
    login_res = client.post("/api/auth/mock-login", json={"role": "admin", "username": "Operator"})
    token = login_res.json()["access_token"]

    # 2. Post bottleneck telemetry (entry rate > 120, wait time > 15)
    headers = {"Authorization": f"Bearer {token}"}
    payload = {
        "gate_name": "Gate B",
        "entry_rate": 130.0,
        "queue_wait_time": 26.0,
        "crowd_density": "critical"
    }
    response = client.post("/api/telemetry", json=payload, headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["bottleneck_detected"] is True
    assert data["alert_created"] is True
