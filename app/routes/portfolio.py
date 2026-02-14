from fastapi import APIRouter, HTTPException
from app.utils.supabase import supabase

router = APIRouter()

@router.get("/")
async def get_portfolio(email: str):
    try:
        profile = supabase.table('profiles').select("*").eq('email', email).single().execute()
        
        # If investor, show mock holdings. If not, show empty.
        is_investor = profile.data.get('is_investor', False) if profile.data else False
        
        return {
            "holdings": [
                {"stock": "Farmland A", "shares": 10, "value": 265000}
            ] if is_investor else [],
            "total_value": 265000 if is_investor else 0,
            "is_investor": is_investor
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
