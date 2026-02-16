"""
Migration script to add land_value and total_profits columns
and reset fund metrics to initial state
"""
from app.utils.supabase import supabase
from datetime import datetime

def run_migration():
    print("=" * 60)
    print("RUNNING MIGRATION: Add Fund Breakdown Columns")
    print("=" * 60)
    
    # Step 1: Add columns via raw SQL
    print("\n1. Adding land_value and total_profits columns...")
    
    migration_sql = """
    DO $$ 
    BEGIN 
        -- Add land_value column
        IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                       WHERE table_name = 'fund_metrics' AND column_name = 'land_value') THEN
            ALTER TABLE fund_metrics ADD COLUMN land_value NUMERIC DEFAULT 0;
            RAISE NOTICE 'Added land_value column to fund_metrics';
        END IF;
        
        -- Add total_profits column
        IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                       WHERE table_name = 'fund_metrics' AND column_name = 'total_profits') THEN
            ALTER TABLE fund_metrics ADD COLUMN total_profits NUMERIC DEFAULT 0;
            RAISE NOTICE 'Added total_profits column to fund_metrics';
        END IF;
    END $$;
    """
    
    try:
        # Note: Supabase Python client doesn't support raw SQL execution directly
        # You need to run this in Supabase SQL Editor or use PostgREST
        print("⚠️  Please run the following SQL in your Supabase SQL Editor:")
        print("-" * 60)
        print(migration_sql)
        print("-" * 60)
        print("\nAfter running the SQL, press Enter to continue...")
        input()
    except Exception as e:
        print(f"❌ Error: {e}")
        return
    
    # Step 2: Reset fund metrics with new columns
    print("\n2. Resetting fund metrics to initial state...")
    
    initial_metrics = {
        "total_fund_value": 26500000,
        "land_value": 0,
        "total_profits": 0,
        "total_stocks": 1000,
        "stock_price": 26500,
        "growth_percentage": 0,
        "phase1_progress": 0,
        "phase2_progress": 0,
        "phase3_progress": 0,
        "total_expenses": 0,
        "updated_at": datetime.utcnow().isoformat()
    }
    
    try:
        result = supabase.table('fund_metrics').insert(initial_metrics).execute()
        print("✅ Fund metrics reset successfully!")
        print(f"   - Total Fund Value: ₹{initial_metrics['total_fund_value']:,}")
        print(f"   - Land Value: ₹{initial_metrics['land_value']:,}")
        print(f"   - Total Profits: ₹{initial_metrics['total_profits']:,}")
    except Exception as e:
        print(f"❌ Error resetting metrics: {e}")
        return
    
    print("\n" + "=" * 60)
    print("MIGRATION COMPLETED SUCCESSFULLY!")
    print("=" * 60)
    print("\n✅ Next steps:")
    print("   1. Refresh your dashboard")
    print("   2. Try adding land value or profit")
    print("   3. Check the Fund Performance graph")

if __name__ == "__main__":
    run_migration()
