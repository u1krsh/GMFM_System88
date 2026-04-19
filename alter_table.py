import os
import sys

# Append the src directory to import local modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))
from supabase import create_client

URL = "https://rymumoqzrxxnnlfwmqyp.supabase.co"
# Admin token required to safely alter tables. 
# We'll run the SQL query via RPC or we can instruct the user to run it.
# Actually, PostgREST doesn't allow executing raw DDL queries (ALTER TABLE) directly via API.
print("To add the username column, you must run this in the Supabase SQL editor:")
print("ALTER TABLE profiles ADD COLUMN username TEXT UNIQUE;")
