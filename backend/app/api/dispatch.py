import logging
import asyncio
import math
import re
from typing import List, Dict, Any, Tuple, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from app.core.security import require_staff_or_admin
from app.core.supabase_client import supabase
from app.core import memory_db

logger = logging.getLogger(__name__)
router = APIRouter()

class DispatchPayload(BaseModel):
    alert_id: str
    staff_id: str

# Coordinates for Hard Rock Stadium, Miami (FIFA 2026 Venue)
LOCATION_COORDINATES: Dict[str, Tuple[float, float]] = {
    "gate a": (25.9585, -80.2395),
    "gate b": (25.9592, -80.2380),
    "gate c": (25.9575, -80.2375),
    "gate d": (25.9568, -80.2390),
    "section 100": (25.9580, -80.2389),
    "section 200": (25.9582, -80.2385),
    "section 300": (25.9578, -80.2392),
    "unknown location": (25.9580, -80.2389)
}

def get_location_coordinates(location_str: str) -> Tuple[float, float]:
    loc_lower = location_str.lower()
    for name, coords in LOCATION_COORDINATES.items():
        if name in loc_lower:
            return coords
    return LOCATION_COORDINATES["unknown location"]

def detect_incident_language(text: str) -> str:
    cleaned = text.lower()
    spanish_keywords = ["ayuda", "dolor", "fuego", "medico", "médico", "emergencia", "pecho", "herida", "policia", "gracias"]
    if any(word in cleaned for word in spanish_keywords):
        return "es"
        
    if re.search(r"[\u0600-\u06ff]", text):
        return "ar"
        
    if re.search(r"[\u3040-\u30ff\u4e00-\u9fff]", text):
        return "ja"
        
    if re.search(r"[\u0400-\u04ff]", text):
        return "ru"
        
    return "en"

def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    R = 6371000.0
    
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)
    
    a = math.sin(delta_phi / 2.0)**2 + \
        math.cos(phi1) * math.cos(phi2) * \
        math.sin(delta_lambda / 2.0)**2
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    
    return R * c

@router.get("/alerts")
async def list_alerts(user: Dict[str, Any] = Depends(require_staff_or_admin)) -> List[Dict[str, Any]]:
    """
    Returns all active alerts. Merges Supabase results with memory fallbacks.
    """
    db_alerts: List[Dict[str, Any]] = []
    try:
        res = await asyncio.to_thread(
            lambda: supabase.table("staff_alerts").select("*").order("created_at", desc=True).execute()
        )
        if res.data:
            db_alerts = res.data
    except Exception as e:
        logger.error(f"Supabase offline. Returning memory alerts: {e}")

    # Merge alerts by matching ID
    alert_map: Dict[str, Dict[str, Any]] = {a["id"]: a for a in memory_db.staff_alerts}
    for da in db_alerts:
        alert_map[da["id"]] = da

    merged = list(alert_map.values())
    # Sort by created_at descending
    merged.sort(key=lambda x: x.get("created_at", ""), reverse=True)
    return merged

@router.post("/assign")
async def assign_dispatch(payload: DispatchPayload, user: Dict[str, Any] = Depends(require_staff_or_admin)) -> Dict[str, Any]:
    """
    Assigns a volunteer/staff to an incident.
    """
    # 1. Update in-memory DB
    updated = False
    for alert in memory_db.staff_alerts:
        if alert["id"] == payload.alert_id:
            alert["status"] = "dispatched"
            alert["assigned_staff_id"] = payload.staff_id
            updated = True
            break
            
    # 2. Update Supabase DB in thread pool
    try:
        await asyncio.to_thread(
            lambda: supabase.table("staff_alerts").update({
                "status": "dispatched",
                "assigned_staff_id": payload.staff_id
            }).eq("id", payload.alert_id).execute()
        )
        updated = True
    except Exception as e:
        logger.error(f"Supabase offline. Dispatched alert stored in memory only: {e}")

    if not updated:
        raise HTTPException(status_code=404, detail="Alert not found.")
        
    return {"status": "success", "message": f"Volunteer {payload.staff_id} successfully dispatched to alert {payload.alert_id}."}

@router.get("/suggestions/{alert_id}")
async def get_dispatch_suggestions(alert_id: str, user: Dict[str, Any] = Depends(require_staff_or_admin)) -> Dict[str, Any]:
    """
    Tags an alert and recommends available staff/volunteers.
    Ranks by Haversine distance and language capabilities.
    """
    alert: Optional[Dict[str, Any]] = None
    try:
        alert_res = await asyncio.to_thread(
            lambda: supabase.table("staff_alerts").select("*").eq("id", alert_id).execute()
        )
        if alert_res.data:
            alert = alert_res.data[0]
    except Exception as e:
        logger.error(f"Supabase offline. Checking memory: {e}")

    if not alert:
        for a in memory_db.staff_alerts:
            if a["id"] == alert_id:
                alert = a
                break
                
    if not alert:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Staff alert with ID {alert_id} not found."
        )

    incident_coords = get_location_coordinates(alert.get("location", ""))
    incident_lang = detect_incident_language(alert.get("description", "") + " " + alert.get("title", ""))

    staff_list: List[Dict[str, Any]] = []
    try:
        staff_res = await asyncio.to_thread(
            lambda: supabase.table("profiles").select("*").eq("role", "staff").eq("is_available", True).execute()
        )
        if staff_res.data:
            staff_list = staff_res.data
    except Exception as e:
        logger.error(f"Supabase offline. Checking memory for staff: {e}")

    if not staff_list:
        staff_list = [p for p in memory_db.profiles.values() if p.get("role") == "staff" and p.get("is_available", True)]

    suggestions: List[Dict[str, Any]] = []
    for staff in staff_list:
        lat = staff.get("latitude")
        lon = staff.get("longitude")
        
        distance = 500.0
        if lat is not None and lon is not None:
            distance = haversine_distance(incident_coords[0], incident_coords[1], lat, lon)

        staff_languages = staff.get("languages", [])
        lang_matched = incident_lang in staff_languages or (incident_lang == "en" and not staff_languages)

        proximity_score = 1000.0 / (distance + 1.0)
        language_score = 500.0 if lang_matched else 0.0
        total_score = proximity_score + language_score

        suggestions.append({
            "staff_id": staff.get("id"),
            "full_name": staff.get("full_name"),
            "email": staff.get("email"),
            "languages": staff_languages,
            "distance_meters": round(distance, 1),
            "language_matched": lang_matched,
            "score": round(total_score, 2)
        })

    suggestions.sort(key=lambda x: x["score"], reverse=True)

    return {
        "alert": alert,
        "detected_language": incident_lang,
        "suggestions": suggestions[:3]
    }
