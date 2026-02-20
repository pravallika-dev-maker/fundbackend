from app.utils.supabase import supabase

def reset_data():
    print("🚀 Starting Global Financial Reset...")
    
    # 1. Clear ALL Investments
    print("🗑️ Clearing all investment records...")
    supabase.table('investments').delete().neq('fund_id', '00000000-0000-0000-0000-000000000000').execute()
    
    # 2. Clear Investment Activity Logs
    print("📑 Clearing investment activity logs...")
    supabase.table('activity_log').delete().eq('type', 'investment_made').execute()
    
    # 3. Reset Fund Metrics (Clear history, keep zero baseline)
    print("📉 Clearing historical metrics...")
    supabase.table('fund_metrics').delete().neq('fund_id', '00000000-0000-0000-0000-000000000000').execute()
    
    # 4. Reset Fund Stocks Table (The source for the Overview cards)
    print("📦 Resetting inventory to full capacity...")
    funds = supabase.table('funds').select('id, total_stocks').execute().data
    for fund in funds:
        fid = fund['id']
        capacity = fund.get('total_stocks') or 1000
        supabase.table('fund_stocks').update({
            "stocks_sold": 0,
            "stocks_available": capacity
        }).eq('fund_id', fid).execute()
        
    print("✅ Financial Reset Complete. All assets now show 0 Raised and 100% Inventory.")

if __name__ == "__main__":
    reset_data()
