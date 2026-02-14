from fastapi import APIRouter, HTTPException
from app.models.schemas import InvestmentRequest
from app.utils.supabase import supabase

router = APIRouter()

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
