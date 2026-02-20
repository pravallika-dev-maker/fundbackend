from app.utils.supabase import supabase

def migrate_timeline_columns():
    print("Migrating funds table to support detailed phase timelines...")
    
    # Supabase Python client doesn't support ALTER TABLE directly through the table() method.
    # Usually, we'd use the SQL editor, but I'll try to check if I can use the rpc or just assume they will be added.
    # Actually, I can't run raw SQL easily through the client without an RPC setup.
    # I will assume the columns exist or need to be added.
    
    print("Please run the following SQL in your Supabase SQL Editor:")
    print("-" * 50)
    print("""
ALTER TABLE funds 
ADD COLUMN IF NOT EXISTS p1_start_date DATE,
ADD COLUMN IF NOT EXISTS p1_end_date DATE,
ADD COLUMN IF NOT EXISTS p2_start_date DATE,
ADD COLUMN IF NOT EXISTS p2_end_date DATE,
ADD COLUMN IF NOT EXISTS p3_start_date DATE,
ADD COLUMN IF NOT EXISTS p3_end_date DATE;
    """)
    print("-" * 50)

if __name__ == "__main__":
    migrate_timeline_columns()
