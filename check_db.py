import os
from supabase import create_client
from dotenv import load_dotenv

load_dotenv()

url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_ANON_KEY")

supabase = create_client(url, key)

try:
    res = supabase.table('fund_arr_history').select('*').limit(1).execute()
    print("Table 'fund_arr_history' exists.")
except Exception as e:
    print(f"Error: {e}")
