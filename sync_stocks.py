from app.utils.supabase import supabase

def synchronize_stocks():
    print("🚀 Synchronizing all funds to 1000 stock division...")
    
    # 1. Fetch all funds
    funds = supabase.table('funds').select('id, target_amount').execute().data
    
    for fund in funds:
        fid = fund['id']
        target = float(fund['target_amount'] or 0)
        stock_price = int(target / 1000)
        
        print(f"Updating {fid}: Target {target} -> Price {stock_price}")
        
        # 2. Update fund baseline
        supabase.table('funds').update({
            "total_stocks": 1000,
            "stock_price": stock_price
        }).eq('id', fid).execute()
        
        # 3. Update inventory tracking
        # Check if record exists in fund_stocks
        stock_check = supabase.table('fund_stocks').select('fund_id').eq('fund_id', fid).execute().data
        if stock_check:
            supabase.table('fund_stocks').update({
                "stocks_sold": 0,
                "stocks_available": 1000
            }).eq('fund_id', fid).execute()
        else:
            supabase.table('fund_stocks').insert({
                "fund_id": fid,
                "stocks_sold": 0,
                "stocks_available": 1000
            }).execute()

    print("✅ All funds normalized to 1000 stocks with updated pricing.")

if __name__ == "__main__":
    synchronize_stocks()
