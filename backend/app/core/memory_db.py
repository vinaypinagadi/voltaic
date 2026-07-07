import uuid
from datetime import datetime, timezone

# Shared in-memory state for fallback demo mode when Supabase is offline
# Ensure the user has a fully interactive experience regardless of DB status.

profiles = {
    "11111111-1111-1111-1111-111111111111": {
        "id": "11111111-1111-1111-1111-111111111111",
        "email": "vinay@fan.worldcup.org",
        "role": "fan",
        "full_name": "Vinay",
        "languages": ["en"]
    },
    "22222222-2222-2222-2222-222222222222": {
        "id": "22222222-2222-2222-2222-222222222222",
        "email": "volunteer@staff.worldcup.org",
        "role": "staff",
        "full_name": "Volunteer",
        "languages": ["en", "es"],
        "latitude": 25.9576,
        "longitude": -80.2376,
        "is_available": True
    },
    "33333333-3333-3333-3333-333333333333": {
        "id": "33333333-3333-3333-3333-333333333333",
        "email": "operator@admin.worldcup.org",
        "role": "admin",
        "full_name": "Operator",
        "languages": ["en"]
    }
}

tickets = {
    "11111111-1111-1111-1111-111111111111": {
        "user_id": "11111111-1111-1111-1111-111111111111",
        "match_id": "WC-2026-M50 (USA vs ARG)",
        "seat_section": "102",
        "seat_row": "M",
        "seat_number": "14",
        "gate": "Gate C"
    }
}

fan_chats = []

stadium_telemetry = []

staff_alerts = [
    {
        "id": "mock-alert-1",
        "title": "Crowd Congestion warning at Gate D",
        "description": "Gate D throughput is extremely low; queue waiting time has reached 25 minutes.",
        "category": "crowd",
        "status": "pending",
        "location": "Gate D",
        "severity": "high",
        "created_at": datetime.now(timezone.utc).isoformat()
    },
    {
        "id": "mock-alert-2",
        "title": "Medical Incident reported near Section 102",
        "description": "Fan reporting heat exhaustion and requesting immediate hydration support.",
        "category": "medical",
        "status": "pending",
        "location": "Section 102",
        "severity": "medium",
        "created_at": datetime.now(timezone.utc).isoformat()
    }
]

def add_telemetry(gate_name: str, entry_rate: float, queue_wait_time: float, crowd_density: str) -> dict:
    item = {
        "id": str(uuid.uuid4()),
        "gate_name": gate_name,
        "entry_rate": entry_rate,
        "queue_wait_time": queue_wait_time,
        "crowd_density": crowd_density,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
    stadium_telemetry.append(item)
    return item

def add_alert(title: str, description: str, category: str, location: str, severity: str) -> dict:
    item = {
        "id": str(uuid.uuid4()),
        "title": title,
        "description": description,
        "category": category,
        "status": "pending",
        "location": location,
        "assigned_staff_id": None,
        "severity": severity,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    staff_alerts.insert(0, item)
    return item
