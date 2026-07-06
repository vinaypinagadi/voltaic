import google.generativeai as genai
from app.core.config import settings
from app.core.supabase_client import supabase

class GeminiAgent:
    def __init__(self):
        if settings.GEMINI_API_KEY:
            genai.configure(api_key=settings.GEMINI_API_KEY)
        self.embed_model = "models/text-embedding-004"
        self.chat_model = "gemini-1.5-flash"

    def get_embedding(self, text: str) -> list[float]:
        """
        Generates 768-dimension embedding for stadium search.
        """
        if not settings.GEMINI_API_KEY:
            # Return mock embedding for tests
            return [0.0] * 768
        try:
            response = genai.embed_content(
                model=self.embed_model,
                contents=text
            )
            return response["embedding"]
        except Exception as e:
            print(f"Error generating embedding: {e}")
            return [0.0] * 768

    def retrieve_context(self, query: str, limit: int = 3) -> str:
        """
        Queries Supabase vector store for matching stadium rules/maps.
        """
        try:
            embedding = self.get_embedding(query)
            res = supabase.rpc(
                "match_stadium_knowledge",
                {
                    "query_embedding": embedding,
                    "match_threshold": 0.1,  # Lower threshold to capture relevant details
                    "match_count": limit
                }
            ).execute()
            
            if not res.data:
                return "No relevant stadium rules or layout maps found in database."
                
            chunks = []
            for item in res.data:
                chunks.append(f"Source: {item.get('metadata', {})}\nContent: {item.get('content', '')}")
            return "\n\n---\n\n".join(chunks)
        except Exception as e:
            print(f"Error in vector RAG lookup: {e}")
            return "Unable to access vector database for stadium rules."

    def generate_chat_stream(self, message: str, user_id: str, history: list[dict] = None):
        """
        Streams answers from Gemini with context-aware prompts.
        """
        if history is None:
            history = []

        # 1. Fetch user's ticket info if available
        ticket_info = "No registered ticket found."
        from app.core.memory_db import tickets
        t = tickets.get(user_id)
        
        try:
            ticket_res = supabase.table("tickets").select("*").eq("user_id", user_id).execute()
            if ticket_res.data:
                t = ticket_res.data[0]
        except Exception as e:
            print(f"Error fetching tickets from Supabase: {e}")

        if t:
            ticket_info = (
                f"Match: {t.get('match_id')}, Gate: {t.get('gate')}, "
                f"Section: {t.get('seat_section')}, Row: {t.get('seat_row')}, "
                f"Seat: {t.get('seat_number')}"
            )

        # 2. Retrieve RAG context
        context = self.retrieve_context(message)

        # 3. Create systemic prompt prioritizing localized accessibility wayfinding
        system_instruction = (
            "You are Voltaic.AI, the official Generative AI Stadium Assistant for the FIFA World Cup 2026.\n"
            "You help fans find seat locations, navigate gates, learn schedules, and find stadium rules.\n\n"
            "CRITICAL DIRECTIVES:\n"
            "- Always prioritize localized stadium navigation over generic city/urban tourism data.\n"
            "- If a user indicates physical constraints (e.g. wheelchair, difficulty walking), you must explicitly "
            "recommend elevator and ramp routes, steering them away from stairs and escalators.\n"
            "- Render answers clearly and gracefully in the user's input language (support mixed-language code-switching).\n\n"
            f"--- USER TICKET DETAILS ---\n{ticket_info}\n\n"
            f"--- STADIUM RULES & LAYOUT KNOWLEDGE ---\n{context}\n\n"
            "Keep responses helpful, friendly, and structured. Do not reference prompt engineering or internal structures."
        )

        # 4. Construct content list for Gemini chat API
        contents = []
        for turn in history:
            role = "user" if turn.get("role") == "user" else "model"
            contents.append({
                "role": role,
                "parts": [turn.get("content", "")]
            })

        contents.append({
            "role": "user",
            "parts": [message]
        })

        if not settings.GEMINI_API_KEY:
            yield f"[MOCK STREAM] Voltaic.AI: Received your message '{message}'. Context was retrieved."
            return

        try:
            model = genai.GenerativeModel(
                model_name=self.chat_model,
                system_instruction=system_instruction
            )
            response = model.generate_content(
                contents=contents,
                stream=True
            )
            for chunk in response:
                if chunk.text:
                    yield chunk.text
        except Exception as e:
            print(f"Gemini generation error: {e}")
            yield f"Error: Failed to generate streaming answer. Details: {str(e)}"
