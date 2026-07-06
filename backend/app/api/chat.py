import logging
import asyncio
import json
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import List, Optional, Any, Dict, AsyncGenerator

from app.core.security import get_current_user
from app.core.guardrails import check_emergency
from app.core.supabase_client import supabase
from app.core.memory_db import tickets, fan_chats, add_alert
from app.agents.gemini_client import GeminiAgent

logger = logging.getLogger(__name__)
router = APIRouter()
agent = GeminiAgent()

class ChatMessage(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    message: str
    history: Optional[List[ChatMessage]] = []

@router.post("/stream")
async def chat_stream(request: ChatRequest, user: Dict[str, Any] = Depends(get_current_user)) -> StreamingResponse:
    """
    Streams chatbot response asynchronously.
    Checks for emergency inputs first and runs deterministic safety response.
    """
    message: str = request.message
    history: List[Dict[str, Any]] = [h.model_dump() for h in request.history]
    
    # 1. Run deterministic guardrails
    emergency: Optional[Dict[str, Any]] = check_emergency(message)
    if emergency:
        # Resolve ticket information to locate user (try Supabase, fallback to memory)
        location: str = "Unknown Location"
        ticket_data: Optional[Dict[str, Any]] = tickets.get(user["id"])
        
        try:
            # Query Supabase in thread pool to prevent blocking the event loop
            ticket_res = await asyncio.to_thread(
                lambda: supabase.table("tickets").select("*").eq("user_id", user["id"]).execute()
            )
            if ticket_res.data:
                ticket_data = ticket_res.data[0]
        except Exception as e:
            logger.error(f"Supabase offline. Locating via memory: {e}")

        if ticket_data:
            location = f"Section {ticket_data.get('seat_section')}, Row {ticket_data.get('seat_row')}, Seat {ticket_data.get('seat_number')} (Gate {ticket_data.get('gate')})"

        # Write emergency incident in memory
        add_alert(
            title=f"Emergency: {emergency['category'].upper()} - {user.get('full_name', 'Fan')}",
            description=f"Incident reported by user: {message}",
            category=emergency["category"],
            location=location,
            severity="critical"
        )
        
        # Log chat message in memory
        fan_chats.append({
            "user_id": user["id"],
            "message": message,
            "response": emergency["response"]
        })

        # Attempt Supabase inserts in thread pool
        try:
            await asyncio.to_thread(
                lambda: supabase.table("staff_alerts").insert({
                    "title": f"Emergency: {emergency['category'].upper()} - {user.get('full_name', 'Fan')}",
                    "description": f"Incident reported by user: {message}",
                    "category": emergency["category"],
                    "status": "pending",
                    "location": location,
                    "severity": "critical"
                }).execute()
            )
        except Exception as e:
            logger.error(f"Failed to insert emergency alert into Supabase: {e}")

        try:
            await asyncio.to_thread(
                lambda: supabase.table("fan_chats").insert({
                    "user_id": user["id"],
                    "message": message,
                    "response": emergency["response"]
                }).execute()
            )
        except Exception as e:
            logger.error(f"Failed to save emergency chat record: {e}")

        async def static_stream() -> AsyncGenerator[str, None]:
            yield emergency["response"]
        
        return StreamingResponse(static_stream(), media_type="text/plain")

    # 2. General AI Chat stream
    async def response_stream() -> AsyncGenerator[str, None]:
        full_chunks: List[str] = []
        async for chunk in agent.generate_chat_stream(message, user["id"], history):
            full_chunks.append(chunk)
            yield chunk
            await asyncio.sleep(0.01)

        full_response: str = "".join(full_chunks)
        
        # Save to memory DB
        fan_chats.append({
            "user_id": user["id"],
            "message": message,
            "response": full_response
        })

        # Save to Supabase in thread pool
        try:
            await asyncio.to_thread(
                lambda: supabase.table("fan_chats").insert({
                    "user_id": user["id"],
                    "message": message,
                    "response": full_response
                }).execute()
            )
        except Exception as e:
            logger.error(f"Failed to write fan chat transaction: {e}")

    return StreamingResponse(response_stream(), media_type="text/plain")
