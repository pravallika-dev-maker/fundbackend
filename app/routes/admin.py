from fastapi import APIRouter, HTTPException
from app.models.schemas import ExpenseRequest, GrowthRequest, ProfitRequest, PhaseProgressRequest, RoadmapUpdateRequest, FundDatesUpdateRequest
from app.utils.supabase import supabase
from datetime import datetime
from typing import Optional

router = APIRouter()

CEO_EMAIL = "vijay@vriksha.ai"

def check_ceo(email: str):
    if email != CEO_EMAIL:
        raise HTTPException(status_code=403, detail="Only the Administrator can perform this action.")

async def get_current_metrics(fund_id: str):
    defaults = {
        "fund_id": fund_id,
        "total_fund_value": 0,
        "total_stocks": 1000,
        "stock_price": 0,
        "growth_percentage": 0,
        "phase1_progress": 0,
        "phase2_progress": 0,
        "phase3_progress": 0,
        "land_value": 0,
        "total_profits": 0,
        "total_expenses": 0
    }
    
    # Filter by fund_id
    response = supabase.table('fund_metrics')\
        .select("*")\
        .eq('fund_id', fund_id)\
        .order('id', desc=True)\
        .limit(1)\
        .execute()
    
    metrics = defaults.copy()
    if response.data:
        db_metrics = response.data[0]
        for key, value in db_metrics.items():
            if value is not None:
                metrics[key] = value
                
    # CRITICAL: If the current metrics have 0 progress, try to find the last record that had STATED progress for THIS fund
    if metrics['phase1_progress'] == 0 and metrics['phase2_progress'] == 0 and metrics['phase3_progress'] == 0:
        history = supabase.table('fund_metrics')\
            .select("phase1_progress, phase2_progress, phase3_progress")\
            .eq('fund_id', fund_id)\
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
        fund_id = metrics.get('fund_id')
        if not fund_id:
            raise ValueError("fund_id is required for updating metrics")

        # Calculate new stock price
        total_val = float(metrics.get('total_fund_value', 0))
        total_stocks_cap = 1000 
        metrics['stock_price'] = int(total_val / total_stocks_cap)
        
        # Recalculate Inventory to be robust for this SPECIFIC fund
        try:
            investments_res = supabase.table('investments')\
                .select('stock_count')\
                .eq('fund_id', fund_id)\
                .execute()
            total_sold = 0
            if investments_res.data:
                total_sold = sum(item.get('stock_count', 0) for item in investments_res.data)
            metrics['total_stocks'] = max(0, 1000 - total_sold)
        except Exception:
            pass
            
        metrics['updated_at'] = datetime.utcnow().isoformat()
        if custom_date and str(custom_date).strip():
            metrics['created_at'] = custom_date
            
        # Self-Healing Schema Check
        try:
            # If the table is empty, we can't get keys this way. 
            # We'll use a standard list of expected business columns and only add timestamps if they appear in a sample row.
            schema_res = supabase.table('fund_metrics').select("*").limit(1).execute()
            
            # CORE BUSINESS COLUMNS (Guaranteed to be there if the table follows our schema)
            core_columns = [
                'fund_id', 'total_fund_value', 'stock_price', 'total_stocks', 
                'growth_percentage', 'phase1_progress', 'phase2_progress', 
                'phase3_progress', 'land_value', 'total_profits', 'total_expenses'
            ]
            
            if schema_res.data and len(schema_res.data) > 0:
                db_columns = list(schema_res.data[0].keys())
            else:
                # If table is empty, only send core business columns to be safe. 
                # Avoid created_at/updated_at unless we are sure they exist.
                db_columns = core_columns

            payload = {k: v for k, v in metrics.items() if k in db_columns}
            
            # Special check for timestamps if they were added to metrics but not in db_columns
            if 'updated_at' in metrics and 'updated_at' in db_columns:
                payload['updated_at'] = metrics['updated_at']
            if 'created_at' in metrics and 'created_at' in db_columns:
                payload['created_at'] = metrics['created_at']

        except Exception as schema_err:
            print(f"Schema check failed, using fallback: {schema_err}")
            # Absolute fallback: Only send the most basic fields
            payload = {k: v for k, v in metrics.items() if k in [
                'fund_id', 'total_fund_value', 'stock_price', 'total_stocks',
                'phase1_progress', 'phase2_progress', 'phase3_progress'
            ]}
        
        payload.pop('id', None)
        try:
            res = supabase.table('fund_metrics').insert(payload).execute()
        except Exception as insert_err:
            msg = str(insert_err).lower()
            if "created_at" in msg or "updated_at" in msg:
                print(f"Insertion failed due to timestamp columns, retrying with core fields only: {insert_err}")
                # Strip all timestamp/id fields and try again
                safe_payload = {k: v for k, v in payload.items() if k not in ['created_at', 'updated_at', 'id']}
                res = supabase.table('fund_metrics').insert(safe_payload).execute()
            else:
                raise insert_err
                
        return payload
    except Exception as e:
        print(f"Sub-error in update_fund_metrics: {str(e)}")
        raise e

@router.post("/add-expense")
async def add_expense(req: ExpenseRequest):
    try:
        check_ceo(req.email)
        effective_date = req.date if (req.date and req.date.strip()) else datetime.utcnow().isoformat()
        
        # 1. Insert into expenses table
        expense_data = req.model_dump(exclude={"email"}) if hasattr(req, 'model_dump') else req.dict(exclude={"email"})
        expense_data['date'] = effective_date
            
        try:
            exp_schema_res = supabase.table('expenses').select("*").limit(1).execute()
            exp_db_cols = exp_schema_res.data[0].keys() if exp_schema_res.data else []
            if exp_db_cols:
                expense_data = {k: v for k, v in expense_data.items() if k in exp_db_cols}
            supabase.table('expenses').insert(expense_data).execute()
        except Exception as ee:
            print(f"Warning: Failed to log to expenses table: {ee}")
        
        # 2. Update fund_metrics
        metrics = await get_current_metrics(req.fund_id)
        metrics.pop('id', None)
        metrics.pop('updated_at', None)
        
        current_expenses = float(metrics.get('total_expenses', 0) or 0)
        metrics['total_expenses'] = int(current_expenses + req.amount)
        
        updated = await update_fund_metrics(metrics, effective_date)
        
        # 3. Log Activity
        log_entry = {
            "fund_id": req.fund_id,
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
        metrics = await get_current_metrics(req.fund_id)
        
        metrics.pop('id', None)
        metrics.pop('updated_at', None)
        effective_date = req.date if (req.date and req.date.strip()) else datetime.utcnow().isoformat()
        
        current_land = float(metrics.get('land_value', 0) or 0)
        metrics['land_value'] = int(current_land + req.amount)
        current_total = float(metrics.get('total_fund_value', 0) or 0)
        metrics['total_fund_value'] = int(current_total + req.amount)
        
        updated = await update_fund_metrics(metrics, effective_date)
        
        log_entry = {
            "fund_id": req.fund_id,
            "type": "land_value_updated",
            "amount": req.amount,
            "email": req.email,
            "created_at": effective_date
        }
        supabase.table('activity_log').insert(log_entry).execute()

        try:
            perf_entry = {
                "fund_id": req.fund_id,
                "type": "land_growth",
                "amount": req.amount,
                "date": effective_date.split('T')[0],
                "updated_by": req.email,
                "description": "Land value appreciation"
            }
            supabase.table('fund_performance_history').insert(perf_entry).execute()
        except Exception as perf_err:
             print(f"Warning: performance history log failed: {perf_err}")
        
        return updated
    except Exception as e:
        print(f"Error in update-growth: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Server Error: {str(e)}")

@router.post("/add-profit")
async def add_profit(req: ProfitRequest):
    try:
        check_ceo(req.email)
        metrics = await get_current_metrics(req.fund_id)
        
        metrics.pop('id', None)
        metrics.pop('updated_at', None)
        effective_date = req.date if (req.date and req.date.strip()) else datetime.utcnow().isoformat()
        
        current_profits = float(metrics.get('total_profits', 0) or 0)
        metrics['total_profits'] = int(current_profits + req.amount)
        current_total = float(metrics.get('total_fund_value', 0) or 0)
        metrics['total_fund_value'] = int(current_total + req.amount)
        
        updated = await update_fund_metrics(metrics, effective_date)
        
        log_entry = {
            "fund_id": req.fund_id,
            "type": "profit_added",
            "amount": req.amount,
            "email": req.email,
            "created_at": effective_date
        }
        supabase.table('activity_log').insert(log_entry).execute()

        try:
            perf_entry = {
                "fund_id": req.fund_id,
                "type": "profit",
                "amount": req.amount,
                "date": effective_date.split('T')[0],
                "updated_by": req.email,
                "description": "Profit addition"
            }
            supabase.table('fund_performance_history').insert(perf_entry).execute()
        except Exception as perf_err:
             print(f"Warning: performance history log failed: {perf_err}")
        
        return updated
    except Exception as e:
        print(f"Error in add-profit: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Server Error: {str(e)}")

@router.post("/update-phase")
async def update_phase(req: PhaseProgressRequest):
    try:
        check_ceo(req.email)
        metrics = await get_current_metrics(req.fund_id)
        
        metrics.pop('id', None)
        metrics.pop('updated_at', None)
        effective_date = req.date if (req.date and req.date.strip()) else datetime.utcnow().isoformat()
        
        metrics['phase1_progress'] = req.phase1
        metrics['phase2_progress'] = req.phase2
        metrics['phase3_progress'] = req.phase3
        
        updated = await update_fund_metrics(metrics, effective_date)
        
        log_entry = {
            "fund_id": req.fund_id,
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

@router.post("/update-roadmap")
async def update_roadmap(req: RoadmapUpdateRequest):
    try:
        check_ceo(req.email)
        roadmap_json = [step.model_dump() for step in req.roadmap]
        
        res = supabase.table('funds').update({"roadmap": roadmap_json}).eq('id', req.fund_id).execute()
        
        log_entry = {
            "fund_id": req.fund_id,
            "type": "roadmap_updated",
            "amount": 0,
            "email": req.email,
            "created_at": datetime.utcnow().isoformat()
        }
        supabase.table('activity_log').insert(log_entry).execute()
        
        return res.data
    except Exception as e:
        print(f"Error in update-roadmap: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Server Error: {str(e)}")

@router.post("/update-fund-dates")
async def update_fund_dates(req: FundDatesUpdateRequest):
    try:
        check_ceo(req.email)
        
        update_data = {
            "entry_date": req.entry_date,
            "exit_date": req.exit_date,
            "p1_start_date": req.p1_start_date,
            "p1_end_date": req.p1_end_date,
            "p2_start_date": req.p2_start_date,
            "p2_end_date": req.p2_end_date,
            "p3_start_date": req.p3_start_date,
            "p3_end_date": req.p3_end_date
        }
        
        res = supabase.table('funds').update(update_data).eq('id', req.fund_id).execute()
        
        log_entry = {
            "fund_id": req.fund_id,
            "type": "dates_updated",
            "amount": 0,
            "email": req.email,
            "created_at": datetime.utcnow().isoformat()
        }
        supabase.table('activity_log').insert(log_entry).execute()
        
        return res.data
    except Exception as e:
        print(f"Error in update-fund-dates: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Server Error: {str(e)}")

@router.get("/activities")
async def get_activities(fundId: Optional[str] = None):
    query = supabase.table('activity_log').select("*")
    if fundId:
        query = query.eq('fund_id', fundId)
    response = query.order('created_at', desc=True).limit(20).execute()
    return response.data

@router.get("/growth-history")
async def get_fund_history(fundId: Optional[str] = None):
    try:
        # Get fund start date first
        start_date = "2024-01-01"
        if fundId:
            fund_res = supabase.table('funds').select('created_at').eq('id', fundId).execute()
            if fund_res.data:
                start_date = fund_res.data[0]['created_at'].split('T')[0]

        query = supabase.table('activity_log').select("*").order('created_at', desc=False)
        if fundId:
            query = query.eq('fund_id', fundId)
            
        response = query.execute()
            
        history_map = {}
        # 1. Initialize with an absolute zero point (Origin)
        # Use a day before start_date to ensure a line is drawn even for new funds
        from datetime import datetime, timedelta
        try:
            prev_date = (datetime.strptime(start_date, '%Y-%m-%d') - timedelta(days=1)).strftime('%Y-%m-%d')
        except:
            prev_date = "2024-01-01"

        history_map[prev_date] = {
            "date": prev_date,
            "landAppreciation": 0,
            "profits": 0,
            "capital": 0,
            "deployment": 0,
            "fundValue": 0,
            "total": 0
        }

        running_land = 0
        running_profits = 0
        running_capital = 0
        running_expenses = 0
        
        for item in response.data:
            itype = item.get('type')
            amount = float(item.get('amount', 0) or 0)
            
            is_relevant = False
            if itype in ['land_value_updated', 'land updated', 'land_growth']:
                running_land += amount
                is_relevant = True
            elif itype in ['profit_added', 'profit_growth']:
                running_profits += amount
                is_relevant = True
            elif itype == 'investment_made':
                running_capital += amount
                is_relevant = True
            elif itype == 'expense_added':
                running_expenses += amount
                is_relevant = True
            elif itype == 'progress_updated':
                is_relevant = True

            if is_relevant:
                timestamp = item.get('created_at', '')
                date_key = timestamp.split('T')[0] if 'T' in timestamp else timestamp[:10]
                
                # Cumulative update
                history_map[date_key] = {
                    "date": date_key,
                    "landAppreciation": running_land,
                    "profits": running_profits,
                    "capital": running_capital,
                    "deployment": running_expenses,
                    "fundValue": running_land + running_profits + running_capital,
                    "total": running_land + running_profits + running_capital
                }
            
        sorted_history = [history_map[k] for k in sorted(history_map.keys())]
        return sorted_history
    except Exception as e:
        print(f"Error in growth history: {e}")
        return []
