from app.utils.supabase import supabase

def update_fund_dates():
    print("Updating fund dates to 2026...")
    
    # Update all funds to start in Jan 2026 and end in Dec 2026
    # This ensures all phase calculations fall within 2026
    res = supabase.table('funds').update({
        "entry_date": "2026-01-01",
        "exit_date": "2026-12-31"
    }).neq('id', '00000000-0000-0000-0000-000000000000').execute()
    
    # Also update the roadmap to be 2026 focused
    roadmap_2026 = [
        {"phase": "Entry", "date": "Jan 26", "status": "Completed"},
        {"phase": "Development", "date": "Mar 26", "status": "Active Stage"},
        {"phase": "Growth", "date": "Jun 26", "status": "Planned"},
        {"phase": "Maturity", "date": "Sep 26", "status": "Planned"},
        {"phase": "Strategic Exit", "date": "Dec 26", "status": "Planned"}
    ]
    
    supabase.table('funds').update({
        "roadmap": roadmap_2026
    }).neq('id', '00000000-0000-0000-0000-000000000000').execute()

    print("Successfully updated all fund entry/exit dates and roadmaps to 2026.")

if __name__ == "__main__":
    update_fund_dates()
