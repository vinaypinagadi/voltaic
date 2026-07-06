-- =============================================================
-- Voltaic.AI — Idempotent Schema for Supabase
-- Safe to run multiple times without "already exists" errors
-- =============================================================

-- Enable the pgvector extension to support embedding queries
CREATE EXTENSION IF NOT EXISTS vector;

-- Enable uuid-ossp extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ===================== TABLES =====================

-- Create Profiles Table (extends auth.users)
CREATE TABLE IF NOT EXISTS public.profiles (
  id UUID PRIMARY KEY REFERENCES auth.users ON DELETE CASCADE,
  email TEXT,
  role TEXT NOT NULL DEFAULT 'fan' CHECK (role IN ('fan', 'staff', 'admin')),
  full_name TEXT,
  languages TEXT[] DEFAULT '{}'::TEXT[],
  latitude DOUBLE PRECISION,
  longitude DOUBLE PRECISION,
  is_available BOOLEAN DEFAULT TRUE,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create Tickets Table
CREATE TABLE IF NOT EXISTS public.tickets (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  user_id UUID NOT NULL REFERENCES auth.users ON DELETE CASCADE,
  match_id TEXT NOT NULL,
  seat_section TEXT NOT NULL,
  seat_row TEXT NOT NULL,
  seat_number TEXT NOT NULL,
  gate TEXT NOT NULL,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create Fan Chats Table
CREATE TABLE IF NOT EXISTS public.fan_chats (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  user_id UUID NOT NULL REFERENCES auth.users ON DELETE CASCADE,
  message TEXT NOT NULL,
  response TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create Stadium Knowledge Table for RAG
CREATE TABLE IF NOT EXISTS public.stadium_knowledge (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  content TEXT NOT NULL,
  metadata JSONB DEFAULT '{}'::JSONB,
  embedding VECTOR(768) NOT NULL
);

-- Create Stadium Telemetry Table
CREATE TABLE IF NOT EXISTS public.stadium_telemetry (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  gate_name TEXT NOT NULL,
  entry_rate DOUBLE PRECISION NOT NULL,
  queue_wait_time DOUBLE PRECISION NOT NULL,
  crowd_density TEXT NOT NULL CHECK (crowd_density IN ('low', 'medium', 'high', 'critical')),
  timestamp TIMESTAMPTZ DEFAULT NOW()
);

-- Create Staff Alerts Table
CREATE TABLE IF NOT EXISTS public.staff_alerts (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  title TEXT NOT NULL,
  description TEXT NOT NULL,
  category TEXT NOT NULL CHECK (category IN ('medical', 'crowd', 'fire', 'transit', 'info')),
  status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'dispatched', 'resolved')),
  location TEXT NOT NULL,
  assigned_staff_id UUID REFERENCES auth.users ON DELETE SET NULL,
  severity TEXT NOT NULL CHECK (severity IN ('low', 'medium', 'high', 'critical')),
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ===================== INDEXES =====================

-- Create HNSW Index on Stadium Knowledge Embedding for sub-200ms RAG lookups
CREATE INDEX IF NOT EXISTS stadium_knowledge_hnsw_idx
  ON public.stadium_knowledge
  USING hnsw (embedding vector_cosine_ops);

-- ===================== FUNCTIONS =====================

-- RPC for similarity search
CREATE OR REPLACE FUNCTION match_stadium_knowledge(
  query_embedding VECTOR(768),
  match_threshold DOUBLE PRECISION,
  match_count INT
)
RETURNS TABLE (
  id UUID,
  content TEXT,
  metadata JSONB,
  similarity DOUBLE PRECISION
)
LANGUAGE sql STABLE
AS $$
  SELECT
    id,
    content,
    metadata,
    1 - (stadium_knowledge.embedding <=> query_embedding) AS similarity
  FROM public.stadium_knowledge
  WHERE 1 - (stadium_knowledge.embedding <=> query_embedding) > match_threshold
  ORDER BY stadium_knowledge.embedding <=> query_embedding
  LIMIT match_count;
$$;

-- Automatically sync profiles from auth.users
CREATE OR REPLACE FUNCTION public.handle_new_user()
RETURNS TRIGGER AS $$
BEGIN
  INSERT INTO public.profiles (id, email, role, full_name, languages, latitude, longitude, is_available)
  VALUES (
    new.id,
    new.email,
    COALESCE(new.raw_user_meta_data->>'role', 'fan'),
    COALESCE(new.raw_user_meta_data->>'full_name', 'User'),
    ARRAY(SELECT jsonb_array_elements_text(COALESCE(new.raw_user_meta_data->'languages', '[]'::jsonb))),
    (new.raw_user_meta_data->>'latitude')::DOUBLE PRECISION,
    (new.raw_user_meta_data->>'longitude')::DOUBLE PRECISION,
    COALESCE((new.raw_user_meta_data->>'is_available')::BOOLEAN, TRUE)
  );
  RETURN new;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Helper function to get current user's role securely
CREATE OR REPLACE FUNCTION public.get_user_role()
RETURNS TEXT
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
STABLE
AS $$
DECLARE
  r TEXT;
BEGIN
  IF auth.uid() IS NULL THEN
    RETURN NULL;
  END IF;

  -- First check app_metadata (from JWT)
  r := auth.jwt() -> 'app_metadata' ->> 'role';
  IF r IS NOT NULL THEN
    RETURN r;
  END IF;

  -- Fallback to public.profiles database table
  SELECT role INTO r FROM public.profiles WHERE id = auth.uid();
  RETURN COALESCE(r, 'fan');
END;
$$;

-- ===================== TRIGGERS =====================

-- Drop then recreate to avoid "trigger already exists" error
DROP TRIGGER IF EXISTS on_auth_user_created ON auth.users;

CREATE TRIGGER on_auth_user_created
  AFTER INSERT ON auth.users
  FOR EACH ROW EXECUTE PROCEDURE public.handle_new_user();

-- ===================== ROW LEVEL SECURITY =====================

ALTER TABLE public.profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.tickets ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.fan_chats ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.stadium_knowledge ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.stadium_telemetry ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.staff_alerts ENABLE ROW LEVEL SECURITY;

-- ===================== RLS POLICIES =====================
-- Using DROP POLICY IF EXISTS before each CREATE to be idempotent

-- 1. Profiles
DROP POLICY IF EXISTS "Users can view their own profile" ON public.profiles;
CREATE POLICY "Users can view their own profile"
  ON public.profiles FOR SELECT
  TO authenticated
  USING (auth.uid() = id);

DROP POLICY IF EXISTS "Staff and admin can view all profiles" ON public.profiles;
CREATE POLICY "Staff and admin can view all profiles"
  ON public.profiles FOR SELECT
  TO authenticated
  USING (
    public.get_user_role() IN ('admin', 'staff')
  );

DROP POLICY IF EXISTS "Staff and admin can update profiles" ON public.profiles;
CREATE POLICY "Staff and admin can update profiles"
  ON public.profiles FOR UPDATE
  TO authenticated
  USING (
    public.get_user_role() IN ('admin', 'staff')
  );

-- 2. Tickets
DROP POLICY IF EXISTS "Users can view their own tickets" ON public.tickets;
CREATE POLICY "Users can view their own tickets"
  ON public.tickets FOR SELECT
  TO authenticated
  USING (auth.uid() = user_id);

DROP POLICY IF EXISTS "Users can update their own tickets" ON public.tickets;
CREATE POLICY "Users can update their own tickets"
  ON public.tickets FOR UPDATE
  TO authenticated
  USING (auth.uid() = user_id);

-- 3. Fan Chats
DROP POLICY IF EXISTS "Users can view their own chats" ON public.fan_chats;
CREATE POLICY "Users can view their own chats"
  ON public.fan_chats FOR SELECT
  TO authenticated
  USING (auth.uid() = user_id);

DROP POLICY IF EXISTS "Users can insert their own chats" ON public.fan_chats;
CREATE POLICY "Users can insert their own chats"
  ON public.fan_chats FOR INSERT
  TO authenticated
  WITH CHECK (auth.uid() = user_id);

-- 4. Stadium Knowledge
DROP POLICY IF EXISTS "Anyone can view stadium knowledge" ON public.stadium_knowledge;
CREATE POLICY "Anyone can view stadium knowledge"
  ON public.stadium_knowledge FOR SELECT
  TO authenticated
  USING (TRUE);

DROP POLICY IF EXISTS "Admin and staff can manage stadium knowledge" ON public.stadium_knowledge;
CREATE POLICY "Admin and staff can manage stadium knowledge"
  ON public.stadium_knowledge FOR ALL
  TO authenticated
  USING (
    public.get_user_role() IN ('admin', 'staff')
  );

-- 5. Stadium Telemetry
DROP POLICY IF EXISTS "Staff and admin can view telemetry" ON public.stadium_telemetry;
CREATE POLICY "Staff and admin can view telemetry"
  ON public.stadium_telemetry FOR SELECT
  TO authenticated
  USING (
    public.get_user_role() IN ('admin', 'staff')
  );

DROP POLICY IF EXISTS "Staff and admin can insert telemetry" ON public.stadium_telemetry;
CREATE POLICY "Staff and admin can insert telemetry"
  ON public.stadium_telemetry FOR INSERT
  TO authenticated
  WITH CHECK (
    public.get_user_role() IN ('admin', 'staff')
  );

-- 6. Staff Alerts
DROP POLICY IF EXISTS "Staff and admin can view all alerts" ON public.staff_alerts;
CREATE POLICY "Staff and admin can view all alerts"
  ON public.staff_alerts FOR SELECT
  TO authenticated
  USING (
    public.get_user_role() IN ('admin', 'staff')
  );

DROP POLICY IF EXISTS "Staff and admin can update all alerts" ON public.staff_alerts;
CREATE POLICY "Staff and admin can update all alerts"
  ON public.staff_alerts FOR UPDATE
  TO authenticated
  USING (
    public.get_user_role() IN ('admin', 'staff')
  );

DROP POLICY IF EXISTS "Anyone can insert alerts" ON public.staff_alerts;
CREATE POLICY "Anyone can insert alerts"
  ON public.staff_alerts FOR INSERT
  TO authenticated
  WITH CHECK (TRUE);

-- ===================== DONE =====================
-- Schema applied successfully. Safe to re-run at any time.
