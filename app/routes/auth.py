from fastapi import APIRouter, HTTPException
from app.models.schemas import UserCreate, UserLogin, UserProfile, ProfileUpdateRequest
from app.utils.supabase import supabase

router = APIRouter()

@router.post("/signup")
async def signup(user: UserCreate):
    try:
        response = supabase.auth.sign_up({
            "email": user.email,
            "password": user.password
        })
        if not response.user:
            raise HTTPException(status_code=400, detail="Sign up failed")
        
        # Profile is created by DB trigger in Supabase (optional, manual insert if not)
        return {"message": "User created successfully", "user_id": response.user.id}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/login")
async def login(user: UserLogin):
    print(f"Login attempt for: {user.email}")
    try:
        CEO_EMAIL = "vijay@vriksha.ai"
        
        # Try to sign in
        try:
            print("Attempting Supabase sign-in...")
            res = supabase.auth.sign_in_with_password({
                "email": user.email,
                "password": user.password
            })
            print("Sign-in successful")
        except Exception as e:
            error_str = str(e)
            print(f"Sign-in failed: {error_str}")
            
            # If sign in fails, try to auto-create the CEO
            if "Invalid login credentials" in error_str or "User not found" in error_str:
                print("User missing or wrong creds. Attempting auto-signup for CEO...")
                try:
                    signup_res = supabase.auth.sign_up({
                        "email": user.email,
                        "password": user.password
                    })
                    print("Auto-signup request sent")
                    
                    # Try to sign in again after signup
                    res = supabase.auth.sign_in_with_password({
                        "email": user.email,
                        "password": user.password
                    })
                    print("Sign-in after signup successful")
                except Exception as signup_err:
                    signup_error_str = str(signup_err)
                    print(f"Auto-signup/re-signin failed: {signup_error_str}")
                    
                    if "Email confirmation" in signup_error_str:
                        raise HTTPException(status_code=401, detail="Administrator account created, but email confirmation is REQUIRED in your Supabase settings. Please check your email or disable 'Confirm Email' in Supabase Auth settings.")
                    
                    if "already registered" in signup_error_str:
                        raise HTTPException(status_code=401, detail="The Administrator email is already registered. If you forgot the password, you must reset it in the Supabase Dashboard.")
                    
                    raise HTTPException(status_code=401, detail=f"Registration Error: {signup_error_str}")
            else:
                raise HTTPException(status_code=401, detail=f"Auth Error: {error_str}")
            
        if not res.user:
            raise HTTPException(status_code=401, detail="Invalid credentials")
        
        # Fetch Profile
        try:
            profile = supabase.table('profiles').select("*").eq('id', res.user.id).single().execute()
            profile_data = profile.data if profile.data else None
        except Exception as profile_err:
            print(f"Profile fetch error: {str(profile_err)}")
            profile_data = None
        
        if not profile_data:
            print("Profile missing, creating one...")
            new_profile = {
                "id": res.user.id,
                "email": res.user.email,
                "is_investor": False,
                "verification_status": "none"
            }
            profile_res = supabase.table('profiles').insert(new_profile).execute()
            profile_data = profile_res.data[0]

        return profile_data

    except HTTPException:
        raise
    except Exception as e:
        print(f"Unexpected error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/update-profile")
async def update_profile(req: ProfileUpdateRequest):
    try:
        data = req.dict(exclude_unset=True)
        email = data.pop('email')
        
        response = supabase.table('profiles').update(data).eq('email', email).execute()
        
        if not response.data:
            raise HTTPException(status_code=404, detail="Profile not found")
            
        return response.data[0]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
