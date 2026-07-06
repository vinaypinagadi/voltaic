from supabase import create_client, Client
from app.core.config import settings

# Initialize Supabase client with the service role key to allow backend actions
# such as querying RAG embeddings, logging alerts, and retrieving tickets safely.
supabase: Client = create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_ROLE_KEY)
