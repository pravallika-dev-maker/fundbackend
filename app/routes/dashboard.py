from fastapi import APIRouter, HTTPException
from app.models.schemas import FundMetrics, AllocationItem
from app.utils.supabase import supabase
from typing import List, Optional
from app.utils.calculations import (
    get_daily_expenses, get_monthly_expenses, get_yearly_expenses, 
    get_phase_wise_expenses, get_category_wise_expenses,
    get_monthly_category_breakdown
)

router = APIRouter()

@router.get("/funds")
async def list_funds():
    try:
        # 1. Fetch all funds
        res = supabase.table('funds').select("*").execute()
        funds = res.data
        
        # 2. Enrich with live investment and valuation data
        for fund in funds:
            fid = fund['id']
            target_amount = float(fund.get('target_amount') or 0)
            
            # A. Live Investment Stats
            inv_res = supabase.table('investments').select('stock_count, amount_paid').eq('fund_id', fid).execute()
            total_sold = 0
            actual_raised = 0
            if inv_res.data:
                total_sold = sum(item.get('stock_count', 0) for item in inv_res.data)
                actual_raised = sum(float(item.get('amount_paid', 0) or 0) for item in inv_res.data)
            
            # B. Valuation Stats (Land Growth + Profits)
            # Fetch latest snapshot to get land_value and total_profits
            metrics_res = supabase.table('fund_metrics').select('land_value, total_profits, total_stocks')\
                .eq('fund_id', fid).order('id', desc=True).limit(1).execute()
            
            land_val = 0
            profits = 0
            capacity = fund.get('total_stocks') or 1000
            
            if metrics_res.data:
                m = metrics_res.data[0]
                land_val = float(m.get('land_value') or 0)
                profits = float(m.get('total_profits') or 0)
                capacity = m.get('total_stocks') or capacity

            # Total Fund Value = Target + Land Appreciation + Profits
            total_fund_value = target_amount + land_val + profits
            
            # Stock Price = Total Value / Capacity
            # Ensure we use int() for clean display as in /metrics endpoint
            current_stock_price = int(total_fund_value / capacity) if capacity > 0 else fund.get('stock_price', 0)
            
            # C. ARR Timeline Calculation (Year 0 -> Year 5)
            # Use specific ARR history if provided by CEO, fallback to calculated growth
            arr_res = supabase.table('fund_arr_history').select('year_label, growth_rate')\
                .eq('fund_id', fid).order('year_label', desc=False).execute()
            
            if arr_res.data:
                # Map specific year labels
                timeline = [{"year": "Y0", "growth": 0}]
                arr_map = {item['year_label']: item['growth_rate'] for item in arr_res.data}
                for i in range(1, 6):
                    label = f"Y{i}"
                    timeline.append({"year": label, "growth": arr_map.get(label, 0)})
            else:
                # Fallback to historical growth calculation if no specific ARR points exist
                history_res = supabase.table('fund_metrics').select('land_value, total_profits, created_at')\
                    .eq('fund_id', fid).order('created_at', desc=False).execute()
                
                timeline = [{"year": "Y0", "growth": 0}]
                if history_res.data:
                    latest_growth_pct = round((land_val + profits) / target_amount * 100, 2) if target_amount > 0 else 0
                    for i in range(1, 6):
                        if len(history_res.data) > i:
                            h = history_res.data[i]
                            h_growth = (float(h.get('land_value') or 0) + float(h.get('total_profits') or 0))
                            pct = round((h_growth / target_amount) * 100, 2) if target_amount > 0 else 0
                            timeline.append({"year": f"Y{i}", "growth": pct})
                        elif i == 1:
                             timeline.append({"year": f"Y{i}", "growth": latest_growth_pct})
                        else:
                            timeline.append({"year": f"Y{i}", "growth": latest_growth_pct})
                else:
                    for i in range(1, 6):
                        timeline.append({"year": f"Y{i}", "growth": 0})
            
            # Attach for frontend consumption
            fund['stocks_sold'] = total_sold
            fund['stocks_available'] = max(0, capacity - total_sold)
            fund['total_raised_capital'] = actual_raised
            fund['stock_price'] = current_stock_price
            fund['total_fund_value'] = total_fund_value
            fund['arr_timeline'] = timeline
            
            # Add a progress field for easy access
            fund['progress_percentage'] = round((total_sold / capacity) * 100, 2) if capacity > 0 else 0
            
        return funds
    except Exception as e:
        print(f"Error listing funds: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/metrics")
async def get_metrics(fundId: Optional[str] = None):
    try:
        # 1. Fetch Fund Baseline (Source of Truth)
        if not fundId:
            # If no ID, use the first available fund as default for the dashboard
            fund_res = supabase.table('funds').select("*").limit(1).execute()
        else:
            fund_res = supabase.table('funds').select("*").eq('id', fundId).execute()
            
        if not fund_res.data:
            raise HTTPException(status_code=404, detail="Fund not found in database")
            
        fund = fund_res.data[0]
        fund_id = fund['id']
        
        # Initialize metrics with fund baseline
        metrics = {
            "fund_name": fund.get('name', "Agricultural Asset"),
            "location": fund.get('location', "Chittoor, AP"),
            "total_capital": float(fund.get('target_amount') or 26500000),
            "entry_date": fund.get('entry_date', "Mar 2024"),
            "exit_date": fund.get('exit_date', "Mar 2029"),
            "current_phase": fund.get('phase', "Growth"),
            "status": fund.get('operational_status', "Active Operations"),
            "total_stocks": 1000,
            "total_sold_stocks": 0,
            "total_raised_capital": 0,
            "land_value": 0,
            "total_profits": 0,
            "total_expenses": 0,
            "total_fund_value": 0,
            "stock_price": 0,
            "phase1_progress": 0,
            "phase2_progress": 0,
            "phase3_progress": 0,
            "roadmap": fund.get('roadmap') or []
        }

        # 2. Get latest performance snapshots
        metrics_res = supabase.table('fund_metrics').select("*")\
            .eq('fund_id', fund_id).order('id', desc=True).limit(1).execute()
        
        if metrics_res.data:
            db_metrics = metrics_res.data[0]
            # Only sync progress and historical accretion values from snapshots
            metrics['phase1_progress'] = db_metrics.get('phase1_progress') or 0
            metrics['phase2_progress'] = db_metrics.get('phase2_progress') or 0
            metrics['phase3_progress'] = db_metrics.get('phase3_progress') or 0
            metrics['land_value'] = float(db_metrics.get('land_value') or 0)
            metrics['total_profits'] = float(db_metrics.get('total_profits') or 0)
            metrics['total_stocks'] = db_metrics.get('total_stocks') or 1000

        # 3. Live Inventory Calculation (Investments Table)
        invest_res = supabase.table('investments').select('stock_count, amount_paid')\
            .eq('fund_id', fund_id).execute()
        
        total_sold = 0
        actual_raised = 0
        if invest_res.data:
            total_sold = sum(item.get('stock_count', 0) for item in invest_res.data)
            actual_raised = sum(float(item.get('amount_paid', 0) or 0) for item in invest_res.data)
        
        total_capacity = metrics.get('total_stocks') or 1000
        metrics['total_sold_stocks'] = total_sold
        metrics['total_stocks'] = max(0, total_capacity - total_sold)
        metrics['total_raised_capital'] = actual_raised

        # 4. Institutional Valuation Logic
        # Total Asset Value = Fund Target + Growth + Realized Profits
        growth = metrics['land_value'] + metrics['total_profits']
        metrics['total_fund_value'] = int(metrics['total_capital'] + growth)
        
        # Stock Price = Total Asset Value / Total Stock Capacity
        metrics['stock_price'] = int(metrics['total_fund_value'] / total_capacity)

        # 5. Live Expense Sync
        exp_res = supabase.table('activity_log').select('amount')\
            .eq('fund_id', fund_id).eq('type', 'expense_added').execute()
        if exp_res.data:
            metrics['total_expenses'] = sum(float(item.get('amount', 0) or 0) for item in exp_res.data)

        # 6. Area Info (Fallback if missing in table)
        metrics['total_area'] = fund.get('total_area', "12.5 Acres")

        # 7. ARR Timeline Calculation (Year 0 -> Year 5)
        # Use specific ARR history if provided by CEO, fallback to calculated growth
        arr_res = supabase.table('fund_arr_history').select('year_label, growth_rate')\
            .eq('fund_id', fund_id).order('year_label', desc=False).execute()
        
        if arr_res.data:
            timeline = [{"year": "Y0", "growth": 0}]
            arr_map = {item['year_label']: item['growth_rate'] for item in arr_res.data}
            for i in range(1, 6):
                label = f"Y{i}"
                timeline.append({"year": label, "growth": arr_map.get(label, 0)})
        else:
            history_res = supabase.table('fund_metrics').select('land_value, total_profits, created_at')\
                .eq('fund_id', fund_id).order('created_at', desc=False).execute()
            
            timeline = [{"year": "Y0", "growth": 0}]
            if history_res.data:
                latest_growth_pct = round((metrics['land_value'] + metrics['total_profits']) / metrics['total_capital'] * 100, 2) if metrics['total_capital'] > 0 else 0
                for i in range(1, 6):
                    if len(history_res.data) > i:
                        h = history_res.data[i]
                        h_growth = (float(h.get('land_value') or 0) + float(h.get('total_profits') or 0))
                        pct = round((h_growth / metrics['total_capital']) * 100, 2) if metrics['total_capital'] > 0 else 0
                        timeline.append({"year": f"Y{i}", "growth": pct})
                    elif i == 1:
                         timeline.append({"year": f"Y{i}", "growth": latest_growth_pct})
                    else:
                        timeline.append({"year": f"Y{i}", "growth": latest_growth_pct})
            else:
                for i in range(1, 6):
                    timeline.append({"year": f"Y{i}", "growth": 0})
        
        metrics['arr_timeline'] = timeline

        return metrics
    except Exception as e:
        print(f"Error fetching metrics: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/allocation")
async def get_allocation(fundId: Optional[str] = None):
    try:
        query = supabase.table('fund_allocation').select("*")
        if fundId:
            query = query.eq('fund_id', fundId)
        
        response = query.execute()
        if not response.data:
            return [
                {"name": "Infrastructure", "value": 15000000},
                {"name": "Plantation", "value": 5000000},
                {"name": "Development", "value": 4000000},
                {"name": "Operations", "value": 2500000}
            ]
        
        aggregated = {}
        for item in response.data:
            name = item.get('category_name') or item.get('phase_name') or "Operation"
            amount = float(item.get('allocated_amount') or item.get('amount') or 0)
            aggregated[name] = aggregated.get(name, 0) + amount
            
        return [{"name": k, "value": v} for k, v in aggregated.items()]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/expenses/analytics")
async def get_expense_analytics(fundId: Optional[str] = None):
    try:
        query = supabase.table('activity_log').select("*").eq('type', 'expense_added')
        if fundId:
            query = query.eq('fund_id', fundId)
            
        response = query.order('created_at', desc=True).execute()
        
        expenses = []
        for log in (response.data or []):
            expenses.append({
                "date": log.get('created_at'),
                "amount": float(log.get('amount', 0) or 0),
                "category": log.get('category') or 'Maintenance',
                "phase": log.get('phase') or 1,
            })
            
        return {
            "daily": get_daily_expenses(expenses),
            "monthly": get_monthly_expenses(expenses),
            "yearly": get_yearly_expenses(expenses),
            "phase_wise": get_phase_wise_expenses(expenses),
            "category_wise": get_category_wise_expenses(expenses),
            "breakdown": get_monthly_category_breakdown(expenses)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/performance")
async def get_performance_analytics(fundId: Optional[str] = None):
    try:
        query = supabase.table('fund_performance_history').select("*")
        if fundId:
            query = query.eq('fund_id', fundId)
            
        perf_response = query.order('recorded_date', desc=False).execute()
        history = perf_response.data if perf_response.data else []
        
        formatted = []
        for item in history:
            d = item.get('recorded_date') or item.get('date')
            if not d: continue
            
            if 'land_growth_value' in item:
                if float(item.get('land_growth_value', 0)) > 0:
                    formatted.append({"date": str(d), "amount": float(item['land_growth_value']), "category": "Land Growth"})
                if float(item.get('profit_value', 0)) > 0:
                    formatted.append({"date": str(d), "amount": float(item['profit_value']), "category": "Profit"})
                if float(item.get('capital_value', 0)) > 0:
                    formatted.append({"date": str(d), "amount": float(item['capital_value']), "category": "Initial Fund"})
            else:
                cat = "Land Growth" if item.get('type') == 'land_growth' else "Profit"
                formatted.append({"date": str(d), "amount": float(item.get('amount', 0)), "category": cat})
            
        formatted.sort(key=lambda x: x['date'])
        return {"breakdown": get_monthly_category_breakdown(formatted)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
