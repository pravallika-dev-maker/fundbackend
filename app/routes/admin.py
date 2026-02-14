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
    response = supabase.table('fund_metrics').select("*").order('updated_at', desc=True).limit(1).execute()
    if not response.data:
        # Default starting metrics
        return {
            "total_fund_value": 26500000,
            "total_stocks": 1000,
            "stock_price": 26500,
            "growth_percentage": 12.5,
            "phase1_progress": 85,
            "phase2_progress": 40,
            "phase3_progress": 15
        }
    return response.data[0]

async def update_fund_metrics(metrics: dict):
    # Calculate new stock price
    metrics['stock_price'] = int(metrics['total_fund_value'] / metrics['total_stocks'])
    metrics['updated_at'] = datetime.utcnow().isoformat()
    
    # Supabase uses 'id' to update, but we might want to insert a new row for history
    # For now, let's insert a new row to keep history, and get_metrics always gets the latest
    supabase.table('fund_metrics').insert(metrics).execute()
    return metrics

@router.post("/add-expense")
async def add_expense(req: ExpenseRequest):
    check_ceo(req.email)
    metrics = await get_current_metrics()
    
    # Remove 'id' and 'updated_at' if they exist to insert fresh
    metrics.pop('id', None)
    metrics.pop('updated_at', None)
    
    metrics['total_fund_value'] -= req.amount
    updated = await update_fund_metrics(metrics)
    
    # Log Activity (optional but good)
    supabase.table('activity_log').insert({
        "type": "expense_added",
        "amount": req.amount,
        "email": req.email
    }).execute()
    
    return updated

@router.post("/update-growth")
async def update_growth(req: GrowthRequest):
    check_ceo(req.email)
    metrics = await get_current_metrics()
    
    metrics.pop('id', None)
    metrics.pop('updated_at', None)
    
    metrics['total_fund_value'] += req.amount
    # Calculate growth percentage increase (simple version)
    growth_inc = (req.amount / metrics['total_fund_value']) * 100
    metrics['growth_percentage'] = round(metrics.get('growth_percentage', 0) + growth_inc, 2)
    
    updated = await update_fund_metrics(metrics)
    
    supabase.table('activity_log').insert({
        "type": "land_value_updated",
        "amount": req.amount,
        "email": req.email
    }).execute()
    
    return updated

@router.post("/add-profit")
async def add_profit(req: ProfitRequest):
    check_ceo(req.email)
    metrics = await get_current_metrics()
    
    metrics.pop('id', None)
    metrics.pop('updated_at', None)
    
    metrics['total_fund_value'] += req.amount
    updated = await update_fund_metrics(metrics)
    
    supabase.table('activity_log').insert({
        "type": "profit_added",
        "amount": req.amount,
        "email": req.email
    }).execute()
    
    return updated

@router.post("/update-phase")
async def update_phase(req: PhaseProgressRequest):
    check_ceo(req.email)
    metrics = await get_current_metrics()
    
    metrics.pop('id', None)
    metrics.pop('updated_at', None)
    
    metrics['phase1_progress'] = req.phase1
    metrics['phase2_progress'] = req.phase2
    metrics['phase3_progress'] = req.phase3
    
    updated = await update_fund_metrics(metrics)
    
    supabase.table('activity_log').insert({
        "type": "progress_updated",
        "amount": 0,
        "email": req.email
    }).execute()
    
    return updated

@router.get("/activities")
async def get_activities():
    response = supabase.table('activity_log').select("*").order('created_at', desc=True).limit(10).execute()
    return response.data
