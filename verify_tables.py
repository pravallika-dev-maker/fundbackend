import os
from supabase import create_client
from dotenv import load_dotenv

load_dotenv()

url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_ANON_KEY")

if not url or not key:
    print("Error: SUPABASE_URL or SUPABASE_ANON_KEY not found in .env")
    exit(1)

supabase = create_client(url, key)

tables_to_check = ['fund_managers', 'funds', 'profiles']

for table in tables_to_check:
    print(f"\nChecking table: {table}")
    try:
        # Try to select one record to see if it even exists
        res = supabase.table(table).select('*').limit(1).execute()
        print(f"✅ Table '{table}' exists.")
        
        # Check specific columns if possible by checking the first row
        if res.data:
            print(f"Columns present: {list(res.data[0].keys())}")
        else:
            print("Table is empty, cannot verify columns through select.")
            
    except Exception as e:
        print(f"❌ Error checking table '{table}': {e}")

print("\nAttempting a test insert into fund_managers...")
try:
    test_data = {
        "name": "Test Manager",
        "email": "test_manager@vriksha.ai",
        "phone": "1234567890",
        "created_by_ceo": "vijay@vriksha.ai"
    }
    res = supabase.table('fund_managers').insert(test_data).execute()
    print("✅ Test insert successful!")
    # Cleanup
    supabase.table('fund_managers').delete().eq('email', 'test_manager@vriksha.ai').execute()
except Exception as e:
    print(f"❌ Test insert failed: {e}")
