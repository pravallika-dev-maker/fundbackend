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
        total_stocks_cap = 1000 
        metrics['stock_price'] = int(total_val / total_stocks_cap)
        
        # Recalculate Inventory to be robust
        try:
            investments_res = supabase.table('investments').select('stock_count').execute()
            total_sold = 0
            if investments_res.data:
                total_sold = sum(item.get('stock_count', 0) for item in investments_res.data)
            metrics['total_stocks'] = max(0, 1000 - total_sold)
        except Exception:
            pass # Use whatever is in metrics
            
        metrics['updated_at'] = datetime.utcnow().isoformat()
        if custom_date and str(custom_date).strip():
            metrics['created_at'] = custom_date
            
        # 1. Self-Healing Schema Check: Get actual columns in the database
        try:
            schema_res = supabase.table('fund_metrics').select("*").limit(1).execute()
            db_columns = schema_res.data[0].keys() if schema_res.data else []
        except Exception:
            # Fallback to a safe minimum if check fails
            db_columns = ['total_fund_value', 'stock_price', 'total_stocks', 'created_at', 'updated_at']

        # 2. Filter payload to ONLY include columns that actually exist in the DB
        payload = {k: v for k, v in metrics.items() if (not db_columns or k in db_columns)}
        
        # Safety: Remove id/sensitive if accidently included
        payload.pop('id', None)
        
        res = supabase.table('fund_metrics').insert(payload).execute()
        return payload
    except Exception as e:
        print(f"Sub-error in update_fund_metrics: {str(e)}")
        raise e

@router.post("/add-expense")
async def add_expense(req: ExpenseRequest):
    try:
        check_ceo(req.email)
        
        # Normalize date
        effective_date = req.date if (req.date and req.date.strip()) else datetime.utcnow().isoformat()
        
        # 1. Insert into expenses table
        expense_data = req.model_dump(exclude={"email"}) if hasattr(req, 'model_dump') else req.dict(exclude={"email"})
        expense_data['date'] = effective_date
            
        try:
            # Self-healing schema filter for expenses table
            try:
                exp_schema_res = supabase.table('expenses').select("*").limit(1).execute()
                exp_db_cols = exp_schema_res.data[0].keys() if exp_schema_res.data else []
                if exp_db_cols:
                    expense_data = {k: v for k, v in expense_data.items() if k in exp_db_cols}
            except Exception:
                pass # Try raw insert if check fails

            supabase.table('expenses').insert(expense_data).execute()
        except Exception as ee:
            print(f"Warning: Failed to log to expenses table: {ee}")
        
        # 2. Update fund_metrics
        metrics = await get_current_metrics()
        metrics.pop('id', None)
        metrics.pop('updated_at', None)
        
        # Calculate new total expense
        current_expenses = float(metrics.get('total_expenses', 0) or 0)
        metrics['total_expenses'] = int(current_expenses + req.amount)
        
        updated = await update_fund_metrics(metrics, effective_date)
        
        # 3. Log Activity (Single Source of Truth)
        log_entry = {
            "type": "expense_added",
            "amount": req.amount,
            "email": req.email,
            "category": req.category,
            "phase": req.phase,
            "created_at": effective_date
        }
        try:
            supabase.table('activity_log').insert(log_entry).execute()
        except Exception as ae:
            print(f"Warning: Activity log failed: {ae}")
        
        return updated
    except Exception as e:
        print(f"Error in add-expense: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/update-growth")
async def update_growth(req: GrowthRequest):
    try:
        check_ceo(req.email)
        metrics = await get_current_metrics()
        
        metrics.pop('id', None)
        metrics.pop('updated_at', None)
        
        # Normalize date
        effective_date = req.date if (req.date and req.date.strip()) else datetime.utcnow().isoformat()
        
        # Update land value AND master total fund value (Valuation increases)
        current_land = float(metrics.get('land_value', 0) or 0)
        metrics['land_value'] = int(current_land + req.amount)
        
        current_total = float(metrics.get('total_fund_value', 0) or 0)
        metrics['total_fund_value'] = int(current_total + req.amount)
        
        updated = await update_fund_metrics(metrics, effective_date)
        
        # Standardized event type for financial timeline
        log_entry = {
            "type": "land_value_updated",
            "amount": req.amount,
            "email": req.email,
            "created_at": effective_date
        }
        supabase.table('activity_log').insert(log_entry).execute()

        # NEW: Log to dedicated performance history table
        try:
            perf_entry = {
                "type": "land_growth",
                "amount": req.amount,
                "date": effective_date.split('T')[0],
                "updated_by": req.email,
                "description": "Land value appreciation"
            }
            supabase.table('fund_performance_history').insert(perf_entry).execute()
        except Exception as perf_err:
             print(f"Warning: Could not log to fund_performance_history (Migration likely needed): {perf_err}")
        
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
        
        # Normalize date
        effective_date = req.date if (req.date and req.date.strip()) else datetime.utcnow().isoformat()
        
        # Update profits AND master total fund value (Valuation increases)
        current_profits = float(metrics.get('total_profits', 0) or 0)
        metrics['total_profits'] = int(current_profits + req.amount)
        
        current_total = float(metrics.get('total_fund_value', 0) or 0)
        metrics['total_fund_value'] = int(current_total + req.amount)
        
        updated = await update_fund_metrics(metrics, effective_date)
        
        # Standardized event type for financial timeline
        log_entry = {
            "type": "profit_added",
            "amount": req.amount,
            "email": req.email,
            "created_at": effective_date
        }
        supabase.table('activity_log').insert(log_entry).execute()

        # NEW: Log to dedicated performance history table
        try:
            perf_entry = {
                "type": "profit",
                "amount": req.amount,
                "date": effective_date.split('T')[0],
                "updated_by": req.email,
                "description": "Profit distribution/addition"
            }
            supabase.table('fund_performance_history').insert(perf_entry).execute()
        except Exception as perf_err:
             print(f"Warning: Could not log to fund_performance_history (Migration likely needed): {perf_err}")
        
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
        
        # Normalize date
        effective_date = req.date if (req.date and req.date.strip()) else datetime.utcnow().isoformat()
        
        metrics['phase1_progress'] = req.phase1
        metrics['phase2_progress'] = req.phase2
        metrics['phase3_progress'] = req.phase3
        
        updated = await update_fund_metrics(metrics, effective_date)
        
        log_entry = {
            "type": "progress_updated",
            "amount": 0,
            "email": req.email,
            "created_at": effective_date
        }
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
