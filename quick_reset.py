"""
Quick fix: Reset fund metrics with new structure
This assumes the columns already exist or will be created automatically
"""
from app.utils.supabase import supabase
from datetime import datetime

def quick_reset():
    print("Resetting fund metrics to initial state...")
    print("=" * 60)
    
    # Delete all existing metrics and logs
    try:
        print("1. Clearing old data...")
        supabase.table('fund_metrics').delete().neq('id', '00000000-0000-0000-0000-000000000000').execute()
        supabase.table('activity_log').delete().neq('email', 'system@reset.com').execute()
        supabase.table('expenses').delete().neq('title', 'SystemReset').execute()
        print("   Metrics, activity logs, and expenses cleared")
    except Exception as e:
        print(f"   Warning clearing tables: {e}")
    
    # Insert fresh metrics with new structure
    initial_metrics = {
        "total_fund_value": 26500000,
        "land_value": 0,
        "total_profits": 0,
        "total_stocks": 1000,
        "stock_price": 26500,
        "growth_percentage": 1.5,
        "phase1_progress": 85,
        "phase2_progress": 40,
        "phase3_progress": 15,
        "total_expenses": 0,
        "created_at": datetime.utcnow().isoformat(),
        "updated_at": datetime.utcnow().isoformat()
    }
    
    try:
        print("\n2. Creating new initial metrics...")
        result = supabase.table('fund_metrics').insert(initial_metrics).execute()
        print("   Fund metrics created successfully!")
        print("\nInitial Values:")
        print(f"   - Total Fund Value: {initial_metrics['total_fund_value']}")
        print(f"   - Land Value: {initial_metrics['land_value']}")
        print(f"   - Total Profits: {initial_metrics['total_profits']}")
        print(f"   - Created At: {initial_metrics['created_at']}")
    except Exception as e:
        print(f"   Error: {e}")
        print("\nIf you see 'column does not exist' error:")
        print("   You need to run the SQL migration first in Supabase SQL Editor")
        print("   See: backend/migrations/add_fund_breakdown_columns.sql")
        return False
    
    print("\n" + "=" * 60)
    print("RESET COMPLETE!")
    print("=" * 60)
    print("\nNext steps:")
    print("   1. Restart your backend server (if running)")
    print("   2. Refresh your dashboard in the browser")
    print("   3. Try adding land value - it should appear in the graph")
    
    return True

if __name__ == "__main__":
    quick_reset()
