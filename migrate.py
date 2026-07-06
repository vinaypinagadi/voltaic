import sys
import os
import json
import psycopg2

# Add backend directory to path to load config
sys.path.append(os.path.join(os.path.dirname(__file__), "backend"))

# Seed data items
stadium_knowledge_data = [
    {
        "content": "Gate A (US Fan Entryway) is located on the North side of the stadium. It features 12 automated ticket scanning lanes and standard escalator access to the upper decks (sections 300-340). Note: Gate A does not have elevator access. Wheelchair users or fans with mobility issues should use Gate D instead.",
        "metadata": {"type": "layout", "gate": "Gate A", "accessibility": "limited"}
    },
    {
        "content": "Gate B (North Corridor) is the heavy transit entrance, located nearest to the subway and shuttle stations. It contains stair-only access to the mid-tier seating sections (200-220). Wheelchair and stroller access is restricted at Gate B; visitors requiring ramp access must follow wayfinding signs to Gate D.",
        "metadata": {"type": "layout", "gate": "Gate B", "accessibility": "none"}
    },
    {
        "content": "Gate C (Standard Lower Deck Access) provides a level entryway to sections 100-115 on the East side. There are no stairs or escalators required to reach seat section 102. It includes standard security checkpoints and companion seating sections.",
        "metadata": {"type": "layout", "gate": "Gate C", "accessibility": "good"}
    },
    {
        "content": "Gate D (South Accessible Entry) is the designated ADA accessible entrance. It features elevator banks directly serving all mid-tier suites and upper deck sections. Fully paved ramp routes connect Gate D to the main parking lot. Recommended for all fans with physical constraints or wheelchair needs.",
        "metadata": {"type": "layout", "gate": "Gate D", "accessibility": "full"}
    },
    {
        "content": "Accessible Seating Policy: Companion and wheelchair seating is located in Row M of sections 101, 102, 103, and 104. Ramps are located next to elevator bank 3, which is accessible directly from Gate D. Standard stadium chairs in these sections can be removed to accommodate wheelchairs.",
        "metadata": {"type": "rules", "topic": "accessibility", "seat_row": "M"}
    },
    {
        "content": "Prohibited Items: Backpacks larger than 12x12x6 inches, coolers, glass bottles, metal cans, laser pointers, and professional video cameras are prohibited inside the stadium. Diaper bags and medical bags are permitted but subject to additional search at any gate.",
        "metadata": {"type": "rules", "topic": "prohibited_items"}
    },
    {
        "content": "Emergency Procedures: In the event of an evacuation, all fans should follow instructions from volunteer staff wearing green high-visibility vests. Ground-level exits are located at Gate A, Gate C, and Gate D. Do not use elevators during an emergency evacuation.",
        "metadata": {"type": "rules", "topic": "emergency"}
    },
    {
        "content": "Match Day Schedule: Gates open 3 hours prior to kickoff. For FIFA World Cup Match 50 (USA vs Argentina), gates open at 17:00 local time, with kickoff scheduled for 20:00. Pre-match opening ceremonies start at 19:15.",
        "metadata": {"type": "schedule", "match_id": "WC-2026-M50 (USA vs ARG)"}
    }
]

def generate_embeddings(items, gemini_key):
    """Generates 768-dimension embeddings using the Google Generative AI SDK."""
    import google.generativeai as genai
    genai.configure(api_key=gemini_key)
    
    print("Generating vector embeddings for stadium knowledge via Gemini API...")
    embedded_items = []
    for idx, item in enumerate(items):
        try:
            print(f" -> Embedding chunk {idx+1}/{len(items)}...")
            response = genai.embed_content(
                model="models/text-embedding-004",
                contents=item["content"]
            )
            embedding = response["embedding"]
            embedded_items.append({
                "content": item["content"],
                "metadata": item["metadata"],
                "embedding": embedding
            })
        except Exception as e:
            print(f"Warning: Failed to generate embedding for chunk {idx+1}: {e}")
            # Fallback to zero vector so migration can complete
            embedded_items.append({
                "content": item["content"],
                "metadata": item["metadata"],
                "embedding": [0.0] * 768
            })
    return embedded_items

def main():
    print("==================================================")
    print("      Voltaic.AI Supabase Migration & Seeding     ")
    print("==================================================")
    
    # 1. Gather Database Password
    db_password = input("Enter your Supabase Database Password: ").strip()
    if not db_password:
        print("Error: Database password is required.")
        return

    # 2. Gather Gemini API Key
    gemini_key = os.getenv("GEMINI_API_KEY", "")
    if not gemini_key:
        gemini_key = input("Enter your Gemini API Key (optional, press Enter to skip): ").strip()
        
    db_host = "db.xukqjrntzlvfhhvjfbwm.supabase.co"
    db_port = 5432
    db_name = "postgres"
    db_user = "postgres"
    
    # 3. Connect to Database
    print(f"\nConnecting to hosted Supabase database at {db_host}...")
    try:
        conn = psycopg2.connect(
            host=db_host,
            port=db_port,
            database=db_name,
            user=db_user,
            password=db_password
        )
        conn.autocommit = False
        cursor = conn.cursor()
        print("Connected successfully!")
    except Exception as e:
        print(f"Connection failed: {e}")
        return

    # 4. Apply Schema Migration
    migration_file = os.path.join(os.path.dirname(__file__), "supabase", "migrations", "20260706000000_init_schema.sql")
    print(f"\nReading migration file: {migration_file}...")
    try:
        with open(migration_file, "r", encoding="utf-8") as f:
            sql_content = f.read()
    except Exception as e:
        print(f"Error reading migration file: {e}")
        conn.close()
        return

    print("Applying schema migrations (tables, indexes, triggers, and functions)...")
    try:
        # Clear existing tables/triggers to ensure a clean idempotent run
        print("Clearing any existing conflicting schema elements...")
        cursor.execute("""
            DROP TABLE IF EXISTS 
                public.profiles, 
                public.tickets, 
                public.fan_chats, 
                public.stadium_knowledge, 
                public.stadium_telemetry, 
                public.staff_alerts 
            CASCADE;
            DROP FUNCTION IF EXISTS public.handle_new_user() CASCADE;
            DROP FUNCTION IF EXISTS public.match_stadium_knowledge(vector, double precision, integer) CASCADE;
        """)
        cursor.execute(sql_content)
        conn.commit()
        print("Schema migrations applied successfully!")
    except Exception as e:
        conn.rollback()
        print(f"Error executing schema migrations: {e}")
        conn.close()
        return

    # 5. Seeding Stadium Knowledge
    print("\nPreparing stadium layout and rules knowledge data...")
    if gemini_key:
        seeded_items = generate_embeddings(stadium_knowledge_data, gemini_key)
    else:
        print("No Gemini API key provided. Seeding with dummy/zero vector embeddings...")
        seeded_items = [
            {
                "content": item["content"],
                "metadata": item["metadata"],
                "embedding": [0.0] * 768
            }
            for item in stadium_knowledge_data
        ]

    print("\nInserting stadium knowledge chunks into database...")
    try:
        # Delete existing to prevent duplication
        cursor.execute("TRUNCATE TABLE public.stadium_knowledge RESTART IDENTITY CASCADE;")
        
        for item in seeded_items:
            cursor.execute(
                """
                INSERT INTO public.stadium_knowledge (content, metadata, embedding)
                VALUES (%s, %s, %s);
                """,
                (item["content"], json.dumps(item["metadata"]), item["embedding"])
            )
        conn.commit()
        print("Stadium knowledge seeded successfully!")
    except Exception as e:
        conn.rollback()
        print(f"Seeding failed: {e}")
    finally:
        conn.close()
        print("\n==================================================")
        print("               Migration Complete!                ")
        print("==================================================")

if __name__ == "__main__":
    main()
