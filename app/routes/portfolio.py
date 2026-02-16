from fastapi import APIRouter, HTTPException
from app.utils.supabase import supabase

router = APIRouter()

@router.get("/")
async def get_portfolio(email: str):
    try:
        # 1. Get profile for totals
        profile = supabase.table('profiles').select("*").eq('email', email).single().execute()
        if not profile.data:
            raise HTTPException(status_code=404, detail="Profile not found")
            
        is_investor = profile.data.get('is_investor', False)
        total_stocks = profile.data.get('total_stocks', 0) or 0
        
        # 2. Get current stock price and fund total stocks for valuation/ownership
        metrics = supabase.table('fund_metrics').select("stock_price, total_stocks").order('id', desc=True).limit(1).execute()
        current_price = metrics.data[0].get('stock_price', 26500) if metrics.data else 26500
        fund_total_stocks = metrics.data[0].get('total_stocks', 1000) if metrics.data else 1000
        
        # 3. Get recent investments for history
        history = supabase.table('investments')\
            .select("*")\
            .eq('email', email)\
            .order('created_at', desc=True)\
            .limit(5)\
            .execute()
        
        return {
            "is_investor": is_investor,
            "total_stocks": total_stocks,
            "stock_price": current_price,
            "fund_total_stocks": fund_total_stocks,
            "total_portfolio_value": total_stocks * current_price,
            "history": history.data or [],
            "holdings": [
                {"stock": "Vriksha Farmland", "shares": total_stocks, "value": total_stocks * current_price}
            ] if total_stocks > 0 else []
        }
    except Exception as e:
        print(f"Error in get_portfolio: {e}")
        raise HTTPException(status_code=500, detail=str(e))
