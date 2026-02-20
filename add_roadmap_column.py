from app.utils.supabase import supabase

def add_roadmap_column():
    print("Attempting to add 'roadmap' column to 'funds' table...")
    
    # We'll use a trick: search if it exists. 
    # Since we can't run raw SQL easily via the client, 
    # we'll try to insert a record with 'roadmap' and see if it fails.
    # Actually, the best way is to provide the SQL to the user or try an RPC if available.
    
    sql = """
    ALTER TABLE funds ADD COLUMN IF NOT EXISTS roadmap JSONB DEFAULT '[
        {"phase": "Entry", "date": "Mar 24", "status": "Completed"},
        {"phase": "Development", "date": "Dec 24", "status": "Active Stage"},
        {"phase": "Growth", "date": "2025-27", "status": "Planned"},
        {"phase": "Maturity", "date": "2028", "status": "Planned"},
        {"phase": "Strategic Exit", "date": "Mar 29", "status": "Planned"}
    ]'::jsonb;
    """
    
    print("\n-------------------------------------------")
    print("PLEASE RUN THIS SQL IN SUPABASE SQL EDITOR:")
    print("-------------------------------------------")
    print(sql)
    print("-------------------------------------------\n")

if __name__ == "__main__":
    add_roadmap_column()
