from app.utils.supabase import supabase

def check_dates():
    res = supabase.table('funds').select('id, name, entry_date, exit_date').execute()
    for row in res.data:
        print(f"Fund: {row['name']} | ID: {row['id']}")
        print(f"  Entry: {row['entry_date']}")
        print(f"  Exit:  {row['exit_date']}")

if __name__ == "__main__":
    check_dates()
