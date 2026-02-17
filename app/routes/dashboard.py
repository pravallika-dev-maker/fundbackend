from fastapi import APIRouter, HTTPException
from app.models.schemas import FundMetrics, AllocationItem
from app.utils.supabase import supabase
from typing import List
from app.utils.calculations import (
    get_daily_expenses, get_monthly_expenses, get_yearly_expenses, 
    get_phase_wise_expenses, get_category_wise_expenses,
    get_monthly_category_breakdown
)

router = APIRouter()

@router.get("/metrics")
async def get_metrics():
    try:
        # Default metrics structure
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

        # 1. Get absolute latest metrics for totals
        metrics_res = supabase.table('fund_metrics').select("*").order('id', desc=True).limit(1).execute()
        
        metrics = defaults.copy()
        if metrics_res.data:
            db_metrics = metrics_res.data[0]
            for key, val in db_metrics.items():
                if val is not None:
                    metrics[key] = val
        
        # 2. Safety Check: If phase progress is 0, check if there's a previous record that actually has progress
        # This prevents a 'reset' or partial update from hiding the project status
        if metrics['phase1_progress'] == 0 and metrics['phase2_progress'] == 0 and metrics['phase3_progress'] == 0:
            # Look for the last record that had STATED progress
            progress_res = supabase.table('fund_metrics')\
                .select("phase1_progress, phase2_progress, phase3_progress")\
                .order('id', desc=True)\
                .not_.is_('phase1_progress', 'null')\
                .execute()
                
            for row in (progress_res.data or []):
                p1 = row.get('phase1_progress', 0)
                p2 = row.get('phase2_progress', 0)
                p3 = row.get('phase3_progress', 0)
                if p1 > 0 or p2 > 0 or p3 > 0:
                    metrics['phase1_progress'] = p1
                    metrics['phase2_progress'] = p2
                    metrics['phase3_progress'] = p3
                    break

        # 4. Ensure stock price is always calculated correctly from the current state
        total_val = float(metrics.get('total_fund_value', 0))
        # Total Authorized Shares is fixed at 1000 effectively for valuation
        total_stocks_cap = 1000 
        metrics['stock_price'] = int(total_val / total_stocks_cap)

        # 3. Calculate "Available Stocks" & "Capital Raised" dynamically from Investment records
        # This is the single source of truth for inventory and funding progress
        try:
            investments_res = supabase.table('investments').select('stock_count').execute()
            total_sold = 0
            
            if investments_res.data:
                total_sold = sum(item.get('stock_count', 0) for item in investments_res.data)
            
            # Inventory = Authorized Cap (1000) - Total Sold
            metrics['total_stocks'] = max(0, 1000 - total_sold)
            
            # Additional CEO Metrics
            metrics['total_sold_stocks'] = total_sold
            # Create a virtual "Raised Capital" based on current valuation if amount_paid is unreliable
            # Or better, just use (Total Fund Value / 1000) * Sold Stocks 
            # But wait, total_fund_value includes the raised capital! 
            # Let's derive it: Raised = Sold Stocks * Current Price (Approx) or just sum amount_paid if available.
            # User said it shows 0, implying amount_paid might be null in DB.
            # Let's use the derived value for display consistency:
            metrics['total_raised_capital'] = total_sold * metrics['stock_price']
            
        except Exception as e:
            print(f"Error calculating inventory/capital: {e}")
            metrics['total_sold_stocks'] = 0
            metrics['total_raised_capital'] = 0
        
        # Calculate remaining target value based on current price
        metrics['remaining_target_value'] = metrics['total_stocks'] * metrics['stock_price']
        
        # 5. Calculate Actual Capital Put In (Initial Capital)
        try:
            cap_res = supabase.table('activity_log')\
                .select("amount")\
                .filter('type', 'in', '("investment_made", "capital_added")')\
                .execute()
            metrics['total_capital'] = sum(float(item.get('amount', 0) or 0) for item in (cap_res.data or []))
        except Exception:
            metrics['total_capital'] = 0

        return metrics
    except Exception as e:
        print(f"Error fetching metrics: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/allocation", response_model=List[AllocationItem])
async def get_allocation():
    try:
        response = supabase.table('fund_allocation').select("phase_name, amount").execute()
        if not response.data:
            return []
        
        # Aggregating amounts by phase name to ensure unique bars
        aggregated = {}
        for i, item in enumerate(response.data):
            # Fallback to enumerating phases if names are missing
            name = item.get('phase_name') or f"Phase {i+1}"
            amount = float(item.get('amount', 0))
            aggregated[name] = aggregated.get(name, 0) + amount
            
        # Return sorted list for consistent display order
        # Key fix: ensure the graph always gets a valid name/value pair
        return [{"name": k, "value": v} for k, v in sorted(aggregated.items())]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/expenses/analytics")
async def get_expense_analytics():
    try:
        # Use activity_log as the Definitive Source of Truth for the Graph
        response = supabase.table('activity_log')\
            .select("*")\
            .eq('type', 'expense_added')\
            .order('created_at', desc=True)\
            .execute()
        
        raw_logs = response.data if response.data else []
        
        # Map activity_log fields to what the calculation utils expect
        expenses = []
        for log in raw_logs:
            amt = float(log.get('amount', 0) or 0)
            
            expenses.append({
                "date": log.get('created_at'),
                "amount": amt,
                "category": log.get('category') or 'Infrastructure', # Fallback for old logs
                "phase": log.get('phase') or 1,                      # Fallback for old logs
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
async def get_performance_analytics():
    try:
        # 1. Fetch appreciation/profits from dedicated table
        perf_response = supabase.table('fund_performance_history').select("*").order('date', desc=False).execute()
        history = perf_response.data if perf_response.data else []
        
        # Adapt for utils
        formatted = []
        
        # Add performance history
        for item in history:
            d = item.get('date')
            if not d: continue
            cat = "Land Growth" if item.get('type') == 'land_growth' else "Profit"
            formatted.append({
                "date": str(d), 
                "amount": float(item.get('amount', 0)),
                "category": cat
            })
            
        # Sort by date to ensure breakdown is chronological
        formatted.sort(key=lambda x: x['date'])
            
        return {
            "breakdown": get_monthly_category_breakdown(formatted),
            "total_land_growth": sum(x['amount'] for x in formatted if x['category'] == "Land Growth"),
            "total_profit": sum(x['amount'] for x in formatted if x['category'] == "Profit")
        }
    except Exception as e:
        print(f"Error fetching performance history: {e}")
        raise HTTPException(status_code=500, detail=str(e))
