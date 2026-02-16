from fastapi import APIRouter, HTTPException
from app.models.schemas import ExpenseRequest, GrowthRequest, ProfitRequest, PhaseProgressRequest
from app.utils.supabase import supabase
from datetime import datetime

router = APIRouter()

CEO_EMAIL = "vijay@vriksha.ai"

def check_ceo(email: str):
    if email != CEO_EMAIL:
        raise HTTPException(status_code=403, detail="Only the Administrator can perform this action.")

async def get_current_metrics():
    defaults = {
        "total_fund_value": 0,
        "total_stocks": 1000,
        "stock_price": 0,
        "growth_percentage": 0,
        "phase1_progress": 85,
        "phase2_progress": 40,
        "phase3_progress": 15,
        "land_value": 0,
        "total_profits": 0,
        "total_expenses": 0
    }
    # Use ID sorting as it's more reliable for finding the last inserted row
    response = supabase.table('fund_metrics').select("*").order('id', desc=True).limit(1).execute()
    
    metrics = defaults.copy()
    if response.data:
        db_metrics = response.data[0]
        # Only overwrite defaults if the database value is NOT null
        for key, value in db_metrics.items():
            if value is not None:
                metrics[key] = value
                
    # CRITICAL: If the current metrics have 0 progress, try to find the last record that had STATED progress
    # This ensures that updates to growth/profit don't carry forward accidental 0s from a reset script
    if metrics['phase1_progress'] == 0 and metrics['phase2_progress'] == 0 and metrics['phase3_progress'] == 0:
        history = supabase.table('fund_metrics')\
            .select("phase1_progress, phase2_progress, phase3_progress")\
            .order('id', desc=True)\
            .execute()
        for row in (history.data or []):
            if row.get('phase1_progress', 0) > 0 or row.get('phase2_progress', 0) > 0 or row.get('phase3_progress', 0) > 0:
                metrics['phase1_progress'] = row['phase1_progress']
                metrics['phase2_progress'] = row['phase2_progress']
                metrics['phase3_progress'] = row['phase3_progress']
                break
                
    return metrics

async def update_fund_metrics(metrics: dict, custom_date: str = None):
    try:
        # Calculate new stock price
        total_val = float(metrics.get('total_fund_value', 0))
        # Total Authorized Shares is fixed at 1000 effectively for valuation
        total_stocks_cap = 1000 
        metrics['stock_price'] = int(total_val / total_stocks_cap)
        
        # Recalculate Inventory to be robust
        try:
            investments_res = supabase.table('investments').select('stock_count').execute()
            total_sold = 0
            if investments_res.data:
                total_sold = sum(item['stock_count'] for item in investments_res.data)
            metrics['total_stocks'] = max(0, 1000 - total_sold)
        except Exception:
            pass # Keep existing value if fetch fails
        metrics['updated_at'] = datetime.utcnow().isoformat()
        
        if custom_date:
            metrics['created_at'] = custom_date
            
        # List of valid columns to prevent 'column does not exist' errors
        VALID_COLUMNS = {
            'total_fund_value', 'total_stocks', 'stock_price', 'growth_percentage',
            'phase1_progress', 'phase2_progress', 'phase3_progress',
            'land_value', 'total_profits', 'total_expenses', 'created_at', 'updated_at'
        }
        
        # Filter metrics to only include valid columns
        payload = {k: v for k, v in metrics.items() if k in VALID_COLUMNS}
        
        res = supabase.table('fund_metrics').insert(payload).execute()
        return payload
    except Exception as e:
        print(f"Sub-error in update_fund_metrics: {str(e)}")
        raise e

@router.post("/add-expense")
async def add_expense(req: ExpenseRequest):
    try:
        check_ceo(req.email)
        
        # 1. Insert into expenses table
        # Pydantic v2 compatibility: use model_dump if available, else dict
        expense_data = req.model_dump(exclude={"email"}) if hasattr(req, 'model_dump') else req.dict(exclude={"email"})
        
        data = supabase.table('expenses').insert(expense_data).execute()
        
        # 2. Update fund_metrics
        metrics = await get_current_metrics()
        
        # Remove 'id' and 'updated_at' if they exist to insert fresh (history pattern)
        metrics.pop('id', None)
        metrics.pop('updated_at', None)
        
        # Ensure total_expenses is treated as a number
        current_expenses = float(metrics.get('total_expenses', 0) or 0)
        metrics['total_expenses'] = int(current_expenses + req.amount)
        
        updated = await update_fund_metrics(metrics, req.date)
        
        # Log Activity
        log_entry = {
            "type": "expense_added",
            "amount": req.amount,
            "email": req.email,
            "date": req.date or datetime.utcnow().date().isoformat()
        }
        if req.date:
            log_entry["created_at"] = req.date
        
        supabase.table('activity_log').insert(log_entry).execute()
        
        return updated
    except Exception as e:
        print(f"Error in add-expense: {str(e)}") # Print to console for debugging
        raise HTTPException(status_code=500, detail=f"Server Error: {str(e)}")

@router.post("/update-growth")
async def update_growth(req: GrowthRequest):
    try:
        check_ceo(req.email)
        metrics = await get_current_metrics()
        
        metrics.pop('id', None)
        metrics.pop('updated_at', None)
        
        # Update land value separately (DO NOT add to total_fund_value)
        # Robustly handle potential None or string values from DB
        current_land = float(metrics.get('land_value', 0) or 0)
        metrics['land_value'] = int(current_land + req.amount)
        
        updated = await update_fund_metrics(metrics, req.date)
        
        # Standardized event type for financial timeline
        log_entry = {
            "type": "land_value_updated",
            "amount": req.amount,
            "email": req.email
        }
        if req.date:
            log_entry["created_at"] = req.date

        supabase.table('activity_log').insert(log_entry).execute()
        
        return updated
    except Exception as e:
        print(f"Error in update-growth: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Server Error: {str(e)}")

@router.post("/add-profit")
async def add_profit(req: ProfitRequest):
    try:
        check_ceo(req.email)
        metrics = await get_current_metrics()
        
        metrics.pop('id', None)
        metrics.pop('updated_at', None)
        
        # Update profits separately
        # Robustly handle potential None or string values from DB
        current_profits = float(metrics.get('total_profits', 0) or 0)
        metrics['total_profits'] = int(current_profits + req.amount)
        
        updated = await update_fund_metrics(metrics, req.date)
        
        # Standardized event type for financial timeline
        log_entry = {
            "type": "profit_added",
            "amount": req.amount,
            "email": req.email
        }
        if req.date:
            log_entry["created_at"] = req.date

        supabase.table('activity_log').insert(log_entry).execute()
        
        return updated
    except Exception as e:
        print(f"Error in add-profit: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Server Error: {str(e)}")

@router.post("/update-phase")
async def update_phase(req: PhaseProgressRequest):
    try:
        check_ceo(req.email)
        metrics = await get_current_metrics()
        
        metrics.pop('id', None)
        metrics.pop('updated_at', None)
        
        metrics['phase1_progress'] = req.phase1
        metrics['phase2_progress'] = req.phase2
        metrics['phase3_progress'] = req.phase3
        
        updated = await update_fund_metrics(metrics, req.date)
        
        log_entry = {
            "type": "progress_updated",
            "amount": 0,
            "email": req.email
        }
        if req.date:
            log_entry["created_at"] = req.date

        supabase.table('activity_log').insert(log_entry).execute()
        
        return updated
    except Exception as e:
        print(f"Error in update-phase: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Server Error: {str(e)}")

@router.get("/activities")
async def get_activities():
    response = supabase.table('activity_log').select("*").order('created_at', desc=True).limit(10).execute()
    return response.data

@router.get("/growth-history")
async def get_fund_history():
    try:
        # Fetch relevant activities in chronological order
        response = supabase.table('activity_log')\
            .select("*")\
            .order('created_at', desc=False)\
            .execute()
            
        history_map = {}
        running_land = 0
        running_profits = 0
        running_capital = 0
        
        for item in response.data:
            itype = item.get('type')
            amount = float(item.get('amount', 0) or 0)
            
            # Match standardized types and update running totals
            is_growth = False
            if itype in ['land_value_updated', 'land updated', 'land_growth']:
                running_land += amount
                is_growth = True
            elif itype in ['profit_added', 'profit_growth']:
                running_profits += amount
                is_growth = True
            elif itype == 'investment_made':
                running_capital += amount
                is_growth = True
            
            if is_growth:
                # Use the date part of created_at as the key to group by day
                # e.g. "2026-02-16T10:00:00" -> "2026-02-16"
                timestamp = item.get('created_at', '')
                date_key = timestamp.split('T')[0] if 'T' in timestamp else timestamp[:10]
                
                # We store the LATEST running total for this day
                history_map[date_key] = {
                    "date": date_key,
                    "land_value": running_land,
                    "profits": running_profits,
                    "capital": running_capital,
                    "total": running_land + running_profits + running_capital
                }
            
        # Convert map back to sorted list
        sorted_history = [history_map[k] for k in sorted(history_map.keys())]
        return sorted_history
    except Exception as e:
        print(f"Error in activity-based growth history: {e}")
        return []
