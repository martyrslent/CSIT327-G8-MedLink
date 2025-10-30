from supabase import create_client, Client
from django.conf import settings
import sys

# Initialize supabase to None first
supabase: Client | None = None

try:
    SUPABASE_URL = settings.SUPABASE_URL
    SUPABASE_ANON_KEY = settings.SUPABASE_ANON_KEY

    if not SUPABASE_URL or not SUPABASE_ANON_KEY:
        # If settings are missing, log the issue and exit cleanly.
        print("CRITICAL ERROR: Supabase URL or Key is missing from Django settings!")
        print(f"URL: {SUPABASE_URL}, Key is present: {bool(SUPABASE_ANON_KEY)}")
        # We can't use the client, so leave it as None
    else:
        # Only initialize if both are present
        supabase = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)
        print("DEBUG: Supabase Client Initialized Successfully.")

except Exception as e:
    # If anything else goes wrong during setup (like a typo in settings.py)
    print(f"CRITICAL ERROR DURING SUPABASE CLIENT SETUP: {e}", file=sys.stderr)
    supabase = None