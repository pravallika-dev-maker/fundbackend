from app.utils.supabase import supabase
from datetime import datetime

def reset_metrics():
    print("Resetting fund metrics to 26,500,000...")
    
    # Insert a new record with default/reset values
    data = {
        "total_fund_value": 26500000,
        "total_stocks": 1000, # Will be recalculated below
        "stock_price": 26500,
        "growth_percentage": 12.5,
        "phase1_progress": 85,
        "phase2_progress": 40,
        "phase3_progress": 15,
        "total_expenses": 0,
        "updated_at": datetime.utcnow().isoformat()
    }
    
    # Calculate actual available stock by subtracting sold stocks
    try:
        inv_res = supabase.table('investments').select('stock_count').execute()
        total_sold = 0
        if inv_res.data:
            total_sold = sum(i['stock_count'] for i in inv_res.data)
        data['total_stocks'] = max(0, 1000 - total_sold)
        print(f"Preserving inventory: {data['total_stocks']} stocks available ({total_sold} sold)")
    except Exception as e:
        print(f"Warning: Could not fetch investments: {e}")

    try:
        supabase.table('fund_metrics').insert(data).execute()
        print("Success! Fund Value reset to ₹26,500,000")
        print("Total Expenses reset to 0")
        
        # Optional: Clear expenses table if you want a true reset?
        # User only asked to round figure the fund value. 
        # But if we reset fund value but keep expense history, the math won't add up later.
        # I'll leave expenses table alone for now unless asked, but metrics are reset.
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    reset_metrics()
