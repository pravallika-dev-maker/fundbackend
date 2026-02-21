from fastapi import APIRouter, HTTPException
from app.models.schemas import (
    ExpenseRequest, GrowthRequest, ProfitRequest, PhaseProgressRequest, 
    RoadmapUpdateRequest, FundDatesUpdateRequest, ARRBulkUpdateRequest,
    ManagerCreateRequest, FundCreateRequest
)
from app.utils.supabase import supabase
from datetime import datetime
from typing import Optional

router = APIRouter()

CEO_EMAIL = "vijay@vriksha.ai"

def check_ceo(email: str):
    if email != CEO_EMAIL:
        raise HTTPException(status_code=403, detail="Only the Administrator can perform this action.")

def check_authorized(email: str, fund_id: str = None):
    """Allow CEO (all funds) or a fund manager (their assigned fund only)."""
    if email == CEO_EMAIL:
        return  # CEO has full access
    # Check if this is a fund manager assigned to the given fund
    try:
        manager_res = supabase.table('fund_managers').select('assigned_fund').eq('email', email).execute()
        if manager_res.data:
            assigned = manager_res.data[0].get('assigned_fund')
            if fund_id and assigned == fund_id:
                return  # Manager is authorized for this fund
            elif not fund_id:
                return  # No fund restriction, manager can proceed
    except Exception:
        pass
    raise HTTPException(status_code=403, detail="Only the Administrator or the assigned Fund Manager can perform this action.")

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
        check_authorized(req.email, req.fund_id)
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
        check_authorized(req.email, req.fund_id)
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
        check_authorized(req.email, req.fund_id)
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
        check_authorized(req.email, req.fund_id)
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

@router.post("/update-arr")
async def update_arr(req: ARRBulkUpdateRequest):
    try:
        check_authorized(req.email, req.fund_id)
        
        results = []
        for update in req.updates:
            # We store these in a dedicated table for the 5-year growth timeline
            entry = {
                "fund_id": req.fund_id,
                "year_label": update.year,
                "growth_rate": update.growth_rate,
                "updated_by": req.email,
                "updated_at": datetime.utcnow().isoformat()
            }
            
            # Check if record for this year already exists for this fund to update instead of insert
            existing = supabase.table('fund_arr_history')\
                .select("*")\
                .eq('fund_id', req.fund_id)\
                .eq('year_label', update.year)\
                .execute()
                
            if existing.data:
                res = supabase.table('fund_arr_history')\
                    .update({"growth_rate": update.growth_rate, "updated_at": datetime.utcnow().isoformat()})\
                    .eq('fund_id', req.fund_id)\
                    .eq('year_label', update.year)\
                    .execute()
            else:
                res = supabase.table('fund_arr_history').insert(entry).execute()
            results.append(res.data)
            
        # Log to activity log
        log_entry = {
            "fund_id": req.fund_id,
            "type": "arr_updated_bulk",
            "amount": len(req.updates),
            "email": req.email,
            "created_at": datetime.utcnow().isoformat()
        }
        supabase.table('activity_log').insert(log_entry).execute()
        
        return results
    except Exception as e:
        print(f"Error in update-arr: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Database sync failed: {str(e)}")

@router.post("/update-roadmap")
async def update_roadmap(req: RoadmapUpdateRequest):
    try:
        check_authorized(req.email, req.fund_id)
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
        check_authorized(req.email, req.fund_id)
        
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
        # Get fund start date and target amount first
        start_date = "2024-01-01"
        target_amount = 26500000.0  # Default fallback
        if fundId:
            # If fundId is a slug (not a UUID), resolve it first
            import re
            is_uuid = re.match(r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$', str(fundId).lower())
            
            if not is_uuid:
                # Search by name-based slug if we don't have a slug column
                # Standard practice: find the fund that matches the name when slugified
                funds_res = supabase.table('funds').select("id, name").execute()
                found_id = None
                for f in (funds_res.data or []):
                    f_slug = f['name'].lower().replace(' ', '-')
                    if f_slug == str(fundId).lower():
                        found_id = f['id']
                        break
                if found_id:
                    fundId = found_id
                else:
                    # Fallback or error
                    pass

        # 1. Fetch Fund Details
        target_amount = 26500000.0
        start_date = "2024-01-01"
        if fundId:
            f_detail = supabase.table('funds').select("created_at, target_amount").eq('id', fundId).execute()
            if f_detail.data:
                start_date = f_detail.data[0]['created_at'].split('T')[0]
                target_amount = float(f_detail.data[0].get('target_amount') or 26500000)

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
            "total": 0,
            "progress": 0
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
                
                # Calculate progress percentage (Raised / Target)
                prog_val = min(100, int((running_capital / target_amount) * 100)) if target_amount > 0 else 0
                
                # Cumulative update
                # Valuation = Invested Capital + Land Growth + Realized Profits
                current_valuation = running_capital + running_land + running_profits

                history_map[date_key] = {
                    "date": date_key,
                    "landAppreciation": running_land,
                    "profits": running_profits,
                    "capital": running_capital,
                    "deployment": running_expenses, # Deployment = Actual Expenses spent
                    "fundValue": current_valuation,
                    "total": current_valuation,
                    "progress": prog_val
                }
            
        sorted_history = [history_map[k] for k in sorted(history_map.keys())]
        return sorted_history
    except Exception as e:
        print(f"Error in growth history: {e}")
        return []

@router.post("/create-manager")
async def create_manager(req: ManagerCreateRequest):
    try:
        check_ceo(req.ceo_email)
        
        manager_data = {
            "name": req.name,
            "email": req.email,
            "phone": req.phone,
            "assigned_fund": req.assigned_fund,
            "created_by_ceo": req.ceo_email,
            "created_at": datetime.utcnow().isoformat()
        }
        
        # Save to fund_managers table
        res = supabase.table('fund_managers').insert(manager_data).execute()
        
        # Update user role to fund_manager in profiles table if it exists
        supabase.table('profiles').update({"role": "fund_manager"}).eq('email', req.email).execute()
        
        return {"status": "success", "data": res.data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/create-fund")
async def create_fund(req: FundCreateRequest):
    try:
        check_ceo(req.ceo_email)
        
        fund_data = {
            "name": req.name,
            "location": req.location,
            "target_amount": req.target_amount,
            "total_stocks": req.total_stocks,
            "stock_price": req.stock_price,
            "entry_date": req.entry_date,
            "exit_date": req.exit_date,
            "phase": req.phase,
            "description": req.description,
            "blueprint_url": req.blueprint_url,
            "created_by_ceo": req.ceo_email,
            "created_at": datetime.utcnow().isoformat()
        }
        
        # Save to funds table
        res = supabase.table('funds').insert(fund_data).execute()
        
        if res.data:
            new_fund_id = res.data[0]['id']
            # Initialize metrics for the new fund
            metrics_data = {
                "fund_id": new_fund_id,
                "land_value": req.land_value or 0,
                "total_profits": 0,
                "phase1_progress": 0,
                "phase2_progress": 0,
                "phase3_progress": 0,
                "total_stocks": req.total_stocks,
                "created_at": datetime.utcnow().isoformat()
            }
            supabase.table('fund_metrics').insert(metrics_data).execute()
            
        return {"status": "success", "data": res.data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
