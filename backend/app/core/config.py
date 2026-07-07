import os
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional

class Settings(BaseSettings):
    SUPABASE_URL: str = os.getenv("SUPABASE_URL", "https://xukqjrntzlvfhhvjfbwm.supabase.co")
    SUPABASE_ANON_KEY: str = os.getenv("SUPABASE_ANON_KEY", "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Inh1a3Fqcm50emx2ZmhodmpmYndtIiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODMzNDg3MDcsImV4cCI6MjA5ODkyNDcwN30.8wzaamfmSYnCPAYc-oIJ98W5rID0r5SVFnKLBCC782g")
    SUPABASE_SERVICE_ROLE_KEY: str = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Inh1a3Fqcm50emx2ZmhodmpmYndtIiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODMzNDg3MDcsImV4cCI6MjA5ODkyNDcwN30.8wzaamfmSYnCPAYc-oIJ98W5rID0r5SVFnKLBCC782g")
    SUPABASE_JWT_SECRET: str = os.getenv("SUPABASE_JWT_SECRET", "mock-jwt-secret-key-at-least-32-chars-long-for-security")
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

settings = Settings()
