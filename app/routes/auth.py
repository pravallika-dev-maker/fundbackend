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
            
            # Try to check fund_managers table for role assignment
            role = "investor"
            assigned_fund = None
            try:
                manager_check = supabase.table('fund_managers').select('*').eq('email', res.user.email).execute()
                if manager_check.data:
                    role = "fund_manager"
                    assigned_fund = manager_check.data[0].get('assigned_fund')
            except Exception as mc_err:
                print(f"Warning: fund_managers check failed: {mc_err}")
            
            # Try inserting full profile with role + assigned_fund
            try:
                new_profile = {
                    "id": res.user.id,
                    "email": res.user.email,
                    "is_investor": False,
                    "verification_status": "none",
                    "role": role,
                    "assigned_fund": assigned_fund
                }
                profile_res = supabase.table('profiles').insert(new_profile).execute()
                profile_data = profile_res.data[0]
            except Exception as insert_err:
                print(f"Warning: Full profile insert failed ({insert_err}), trying without role/assigned_fund...")
                # Fallback: insert without the new columns if they don't exist yet
                try:
                    basic_profile = {
                        "id": res.user.id,
                        "email": res.user.email,
                        "is_investor": False,
                        "verification_status": "none",
                    }
                    profile_res = supabase.table('profiles').insert(basic_profile).execute()
                    profile_data = profile_res.data[0]
                    # Inject role data into the returned dict even if not stored
                    profile_data["role"] = role
                    profile_data["assigned_fund"] = assigned_fund
                except Exception as basic_err:
                    print(f"Error: Basic profile insert also failed: {basic_err}")
                    profile_data = {
                        "id": res.user.id,
                        "email": res.user.email,
                        "is_investor": False,
                        "verification_status": "none",
                        "role": role,
                        "assigned_fund": assigned_fund
                    }
        else:
            # If profile exists, try to sync fund_manager role
            if profile_data.get('role') != 'ceo' and res.user.email != CEO_EMAIL:
                try:
                    manager_check = supabase.table('fund_managers').select('*').eq('email', res.user.email).execute()
                    if manager_check.data:
                        new_role = "fund_manager"
                        assigned_fund = manager_check.data[0].get('assigned_fund')
                        current_role = profile_data.get('role')
                        
                        if current_role != new_role or profile_data.get('assigned_fund') != assigned_fund:
                            try:
                                updates = {"role": new_role, "assigned_fund": assigned_fund}
                                supabase.table('profiles').update(updates).eq('id', res.user.id).execute()
                                profile_data.update(updates)
                            except Exception as upd_err:
                                print(f"Warning: Could not update role/assigned_fund in profiles ({upd_err}). Columns may not exist yet.")
                                # Still inject into the return value so frontend works
                                profile_data["role"] = new_role
                                profile_data["assigned_fund"] = assigned_fund
                except Exception as mc_err:
                    print(f"Warning: fund_managers sync check failed: {mc_err}")

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
