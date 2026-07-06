# Voltaic.AI 🏟️
### FIFA 2026 Intelligent Stadium Operations & Wayfinding Portal

Voltaic.AI is a real-time intelligent operations dashboard and interactive assistant platform designed for the FIFA World Cup 2026. The application streamlines stadium logistics, emergency alerts, entry telemetry, and spectator assistance across three key user roles: **Fans**, **Staff**, and **Operators (Admins)**.

---

## 🚀 Key Features

*   **Intelligent Fan Companion**: Interactive RAG-based AI assistant guiding fans to seat sections, accessibility-friendly gates, schedule events, and stadium guidelines.
*   **Role-Based Dashboards**:
    *   **Fan Portal**: View match-day tickets, chat with the AI companion, and submit alerts.
    *   **Staff Cockpit**: Monitor assigned zones, update availability, track dispatched alerts, and access safety guidelines.
    *   **Admin Console**: Oversee live stadium telemetry (queue wait times, gate crowd densities), broadcast emergency alerts, and view/dispatch incidents.
*   **Secure Role-Based Access Control (RBAC)**: Custom PostgreSQL Row Level Security (RLS) policies enforcing permission boundaries securely without recursion.
*   **Real-time Telemetry Tracking**: Simulated sensor statistics for ingress monitoring and stadium queue bottleneck detection.

---

## 🛠️ Tech Stack

*   **Frontend**: React (v18), TypeScript, Vite, Vanilla CSS.
*   **Backend**: FastAPI (Python 3.11+), Uvicorn, Python-Jose (JWT decoding), Pytest.
*   **Database & Auth**: Supabase (PostgreSQL), `pgvector` (vector embeddings for semantic context search).

---

## 📦 Installation & Setup

Follow these steps to get the project running locally.

### Prerequisites

*   Python 3.11 or higher
*   Node.js (v18+) and npm
*   (Optional) Supabase CLI & Docker (for containerized database testing)

---

### 1. Database Schema & Setup

The database schema and triggers are defined in `supabase/migrations/20260706000000_init_schema.sql`.

If you have a hosted Supabase database or local container, apply the migrations and seed data using the helper script:

```bash
python migrate.py
```

*Note: The backend has built-in in-memory fallback databases for quick testing even when the database container is offline.*

---

### 2. Backend Setup

1. Navigate to the backend directory:
   ```bash
   cd backend
   ```
2. Install the Python dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Run the FastAPI development server:
   ```bash
   python -m uvicorn app.main:app --port 8000
   ```

*The API documentation will be available at [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs).*

#### Running Tests
To run unit and integration tests:
```bash
python -m pytest
```

---

### 3. Frontend Setup

1. Navigate to the frontend directory:
   ```bash
   cd frontend
   ```
2. Install the Node dependencies:
   ```bash
   npm install
   ```
3. Start the Vite development server:
   ```bash
   npm run dev
   ```

*Open your browser and navigate to [http://localhost:5173](http://localhost:5173) to view the portal.*

---

## 🔒 Security & RLS Architecture

To protect sensitive user data, row level security (RLS) is enabled on all PostgreSQL tables. 

### Insecure `user_metadata` Bypass Fix
Supabase Auth's `user_metadata` (e.g. `auth.jwt() -> 'user_metadata'`) is editable client-side and should never be used for security-sensitive boundaries. To enforce secure roles, the project utilizes a custom `SECURITY DEFINER` function:

```sql
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

  -- 1. Check app_metadata (populated via JWT)
  r := auth.jwt() -> 'app_metadata' ->> 'role';
  IF r IS NOT NULL THEN
    RETURN r;
  END IF;

  -- 2. Fall back to secure database lookup
  SELECT role INTO r FROM public.profiles WHERE id = auth.uid();
  RETURN COALESCE(r, 'fan');
END;
$$;
```

RLS policies on tables (`profiles`, `stadium_knowledge`, `stadium_telemetry`, `staff_alerts`) reference this function securely:
```sql
CREATE POLICY "Staff and admin can view all profiles"
  ON public.profiles FOR SELECT
  TO authenticated
  USING (
    public.get_user_role() IN ('admin', 'staff')
  );
```
Using `SECURITY DEFINER` alongside `SET search_path = public` executes the lookup using database-owner privileges, bypassing RLS internally on the `profiles` table to avoid maximum stack depth / infinite recursion errors.
