from fastapi import APIRouter, HTTPException
from app.models.schemas import InvestmentRequest
from app.utils.supabase import supabase
from datetime import datetime

router = APIRouter()

@router.post("/purchase")
async def purchase_stocks(req: InvestmentRequest, email: str):
    try:
        # 1. Get current profile to check existing stocks
        profile_res = supabase.table('profiles').select("total_stocks, is_investor").eq('email', email).single().execute()
        if not profile_res.data:
            raise HTTPException(status_code=404, detail="Profile not found")
        
        current_stocks = profile_res.data.get('total_stocks', 0) or 0
        new_total = current_stocks + req.stock_count
        
        # 2. Update profile with new totals and investor status
        supabase.table('profiles').update({
            "total_stocks": new_total,
            "is_investor": True
        }).eq('email', email).execute()
        
        # 3. Record the transaction in investments table
        purchase_data = {
            "email": email,
            "stock_count": req.stock_count,
            "amount_paid": req.total_amount,
            "status": "completed"
        }
        supabase.table('investments').insert(purchase_data).execute()

        # 4. Update Fund Metrics (Total Value & Stock Price) for the Dashboard
        try:
            metrics_res = supabase.table('fund_metrics').select("*").order('id', desc=True).limit(1).execute()
            if metrics_res.data:
                latest = metrics_res.data[0]
                
                # Calculate "Available Stocks" dynamically from Investment records
                investments_res = supabase.table('investments').select('stock_count').execute()
                total_sold = 0
                if investments_res.data:
                    total_sold = sum(item['stock_count'] for item in investments_res.data)
                
                # NOTE: investments_res might NOT include the *current* purchase yet if insert happened in parallel or transaction isolation is an issue?
                # Actually, we inserted into 'investments' at step 3. So reading it back now should include it.
                # Just to be safe, if Supabase hasn't committed it yet (which it should have), we can rely on decrement or just re-read.
                # Since we are using Supabase HTTP API, each call is a transaction or atomic.
                
                new_inventory = max(0, 1000 - total_sold)
                
                new_metrics = {
                    "total_fund_value": float(latest.get('total_fund_value', 0) or 0) + float(req.total_amount),
                    "total_stocks": new_inventory, # Available inventory based on total sales
                    "phase1_progress": latest.get('phase1_progress', 85),
                    "phase2_progress": latest.get('phase2_progress', 40),
                    "phase3_progress": latest.get('phase3_progress', 15),
                    "land_value": float(latest.get('land_value', 0) or 0),
                    "total_profits": float(latest.get('total_profits', 0) or 0),
                    "total_expenses": float(latest.get('total_expenses', 0) or 0),
                    "updated_at": datetime.utcnow().isoformat(),
                    "created_at": datetime.utcnow().isoformat()
                }
                
                # Recalculate stock price: 
                # Price should be based on Total Authorized Shares (1000), not Available Shares.
                # Price = Total Fund Value / 1000.
                total_cap = 1000 
                new_metrics['stock_price'] = int(new_metrics['total_fund_value'] / total_cap)
                
                supabase.table('fund_metrics').insert(new_metrics).execute()
        except Exception as me:
            print(f"Metrics update sub-error: {me}")

        # 5. Log activity for the Growth History chart on Dashboard
        log_entry = {
            "type": "investment_made",
            "amount": req.total_amount,
            "email": email,
            "created_at": datetime.utcnow().isoformat()
        }
        supabase.table('activity_log').insert(log_entry).execute()
        
        return {
            "message": f"Successfully purchased {req.stock_count} stocks",
            "new_total": new_total,
            "status": "success"
        }
    except Exception as e:
        print(f"Error in purchase_stocks: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/become-investor")
async def become_investor(email: str):
    try:
        response = supabase.table('profiles').update({"is_investor": True}).eq('email', email).execute()
        if not response.data:
            raise HTTPException(status_code=404, detail="Profile not found")
        return {"message": "Role updated to investor", "status": "success"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/verify")
async def verify_kyc(data: dict):
    try:
        # In a real app, you'd store this in a 'verifications' table
        email = data.get('email')
        update = supabase.table('profiles').update({"verification_status": "pending"}).eq('email', email).execute()
        return {"message": "Verification submitted", "status": "pending"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
