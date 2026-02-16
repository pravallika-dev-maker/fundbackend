import os
import sys
from app.utils.supabase import supabase

def run_migration():
    print("Attempting to verify and fix database schema...")
    
    # 1. Check if 'investments' table exists by trying to select from it
    try:
        supabase.table('investments').select("*").limit(1).execute()
        print("✓ 'investments' table exists.")
    except Exception as e:
        if "PGRST204" in str(e) or "42P01" in str(e) or "not found" in str(e).lower():
            print("! 'investments' table is missing.")
            print("Please run the following SQL in your Supabase SQL Editor:")
            print("""
            CREATE TABLE IF NOT EXISTS investments (
                id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
                email TEXT REFERENCES profiles(email),
                stock_count INTEGER NOT NULL,
                amount_paid NUMERIC NOT NULL,
                status TEXT DEFAULT 'completed',
                created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
            );
            """)
        else:
            print(f"Error checking investments table: {e}")

    # 2. Check if 'total_stocks' and 'is_investor' columns exist in 'profiles'
    try:
        res = supabase.table('profiles').select("total_stocks, is_investor").limit(1).execute()
        print("✓ 'profiles.total_stocks' and 'is_investor' columns exist.")
    except Exception as e:
        if "42703" in str(e) or "does not exist" in str(e):
            print("! 'profiles.total_stocks' or 'is_investor' column is missing.")
            print("Please run the following SQL in your Supabase SQL Editor:")
            print("""
            ALTER TABLE profiles ADD COLUMN IF NOT EXISTS total_stocks INTEGER DEFAULT 0;
            ALTER TABLE profiles ADD COLUMN IF NOT EXISTS is_investor BOOLEAN DEFAULT FALSE;
            """)
        else:
            print(f"Error checking profiles columns: {e}")

if __name__ == "__main__":
    run_migration()
