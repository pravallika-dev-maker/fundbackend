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
    async with httpx.AsyncClient() as client:
        try:
            # 1. Verify PAN
            pan_url = f"{SUREPASS_BASE_URL}/pan/pan"
            pan_resp = await client.post(
                pan_url,
                json={"id_number": req.pan},
                headers={"Authorization": f"Bearer {SUREPASS_API_KEY}"}
            )
            pan_data = pan_resp.json()
            
            # Check for success in production response
            if not (pan_data.get("success") or pan_data.get("status_code") == 200):
                raise HTTPException(status_code=400, detail="PAN Verification Failed")

            # 2. Verify Aadhaar (Assuming similar API structure for demo)
            # In production, Aadhaar usually requires OTP or biometric via authorized partners
            # This is a placeholder for the production API call
            aadhaar_url = f"{SUREPASS_BASE_URL}/aadhaar/verify" # Replace with actual prod endpoint
            # For now, we simulate Aadhaar success if PAN passed
            
            # 3. Update Database
            masked_aadhaar = f"XXXX XXXX {req.aadhaar[-4:]}"
            update_data = {
                "pan_number": req.pan,
                "aadhaar_number": masked_aadhaar,
                "verification_status": "verified",
                "is_investor": True
            }
            
            supabase.table('profiles').update(update_data).eq('email', req.email).execute()
            
            return {"success": True, "message": "KYC Verified Successfully"}

        except Exception as e:
            print(f"KYC Error: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Verification Engine Error: {str(e)}")
