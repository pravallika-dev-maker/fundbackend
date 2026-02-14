from fastapi import APIRouter, HTTPException
import httpx
import os
from pydantic import BaseModel
from app.utils.supabase import supabase

router = APIRouter()

SUREPASS_API_KEY = os.getenv("SUREPASS_API_KEY")
SUREPASS_BASE_URL = os.getenv("SUREPASS_BASE_URL", "https://api.surepass.io/api/v1")

class KYCRequest(BaseModel):
    email: str
    pan: str
    aadhaar: str

@router.post("/run-kyc")
async def run_kyc(req: KYCRequest):
    try:
        # No external APIs as requested - Instant Approval Flow
        
        # 1. Mask Aadhaar for security
        masked_aadhaar = f"XXXX XXXX {req.aadhaar[-4:]}"
        
        # 2. Update Database directly
        update_data = {
            "pan_number": req.pan,
            "aadhaar_number": masked_aadhaar,
            "verification_status": "verified",
            "is_investor": True
        }
        
        response = supabase.table('profiles').update(update_data).eq('email', req.email).execute()
        
        if not response.data:
            raise HTTPException(status_code=404, detail="Profile not found to update")
            
        return {"success": True, "message": "KYC Verified Successfully"}

    except Exception as e:
        print(f"KYC Error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
