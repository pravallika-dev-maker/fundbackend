from fastapi import APIRouter, HTTPException
from app.models.schemas import FundMetrics, AllocationItem
from app.utils.supabase import supabase
from typing import List

router = APIRouter()

@router.get("/metrics", response_model=FundMetrics)
async def get_metrics():
    try:
        response = supabase.table('fund_metrics').select("*").order('updated_at', desc=True).limit(1).execute()
        if not response.data:
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
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/allocation", response_model=List[AllocationItem])
async def get_allocation():
    try:
        response = supabase.table('fund_allocation').select("phase_name, amount").execute()
        if not response.data:
            return [
                {"name": "Phase 1", "value": 22000000},
                {"name": "Phase 2", "value": 3575000},
                {"name": "Phase 3", "value": 1410000}
            ]
        
        # Aggregate data by phase name
        aggregated = {}
        for item in response.data:
            name = item['phase_name']
            amount = item['amount']
            aggregated[name] = aggregated.get(name, 0) + amount
            
        return [{"name": k, "value": v} for k, v in aggregated.items()]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
