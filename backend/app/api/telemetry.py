import logging
import asyncio
from typing import Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from app.core.security import require_staff_or_admin
from app.core.supabase_client import supabase
from app.core import memory_db

logger = logging.getLogger(__name__)
router = APIRouter()

class TelemetryPayload(BaseModel):
    gate_name: str
    entry_rate: float        # fans/minute
    queue_wait_time: float   # minutes
    crowd_density: str       # 'low', 'medium', 'high', 'critical'

@router.post("")
async def record_telemetry(payload: TelemetryPayload, user: Dict[str, Any] = Depends(require_staff_or_admin)) -> Dict[str, Any]:
    """
    Saves crowd density and gate telemetry.
    Falls back to memory database if Supabase container is offline.
    """
    telemetry_item: Optional[Dict[str, Any]] = None
    
    # 1. Try DB in thread pool, fallback to memory
    try:
        telemetry_res = await asyncio.to_thread(
            lambda: supabase.table("stadium_telemetry").insert({
                "gate_name": payload.gate_name,
                "entry_rate": payload.entry_rate,
                "queue_wait_time": payload.queue_wait_time,
                "crowd_density": payload.crowd_density
            }).execute()
        )
        if telemetry_res.data:
            telemetry_item = telemetry_res.data[0]
    except Exception as e:
        logger.error(f"Supabase offline. Fallback to memory: {e}")
        
    # Write to memory DB (ensuring availability in cockpit)
    memory_item = memory_db.add_telemetry(
        gate_name=payload.gate_name,
        entry_rate=payload.entry_rate,
        queue_wait_time=payload.queue_wait_time,
        crowd_density=payload.crowd_density
    )
    if not telemetry_item:
        telemetry_item = memory_item

    # 2. Check for bottleneck anomalies
    bottleneck_detected = False
    severity = "low"
    
    # Thresholds: wait time > 15 minutes or entry rate > 120 fans/min
    if payload.queue_wait_time >= 15.0 or payload.entry_rate >= 120.0:
        bottleneck_detected = True
        severity = "high"
        if payload.queue_wait_time >= 25.0:
            severity = "critical"
            
        title = f"Crowd Bottleneck at {payload.gate_name}"
        description = (
            f"Congestion warning: {payload.gate_name} wait time is {payload.queue_wait_time} min "
            f"and flow rate is {payload.entry_rate} fans/min. Crowd density is classified as {payload.crowd_density}."
        )
        
        # Log anomaly alert in memory
        memory_db.add_alert(
            title=title,
            description=description,
            category="crowd",
            location=f"Gate {payload.gate_name}",
            severity=severity
        )
        
        # Attempt DB log in thread pool
        try:
            await asyncio.to_thread(
                lambda: supabase.table("staff_alerts").insert({
                    "title": title,
                    "description": description,
                    "category": "crowd",
                    "status": "pending",
                    "location": f"Gate {payload.gate_name}",
                    "severity": severity
                }).execute()
            )
        except Exception as e:
            logger.error(f"Failed to log bottleneck alert to Supabase: {e}")

    return {
        "status": "success",
        "telemetry": telemetry_item,
        "bottleneck_detected": bottleneck_detected,
        "alert_created": bottleneck_detected
    }
