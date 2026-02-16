from pydantic import BaseModel
from typing import List, Optional

# Auth Schemas
class UserBase(BaseModel):
    email: str

class UserCreate(UserBase):
    password: str

class UserLogin(UserBase):
    password: str

class UserProfile(UserBase):
    id: str
    is_investor: bool
    verification_status: str

class ProfileUpdateRequest(BaseModel):
    email: str
    full_name: Optional[str] = None
    phone: Optional[str] = None
    pan_number: Optional[str] = None
    aadhaar_number: Optional[str] = None
    bank_name: Optional[str] = None
    account_number: Optional[str] = None
    ifsc_code: Optional[str] = None
    verification_status: Optional[str] = None

# Dashboard Schemas
class FundMetrics(BaseModel):
    total_fund_value: int
    total_stocks: int
    stock_price: int
    growth_percentage: float
    phase1_progress: Optional[int] = 85
    phase2_progress: Optional[int] = 40
    phase3_progress: Optional[int] = 15

class AllocationItem(BaseModel):
    name: str
    value: int

# Invest Schemas
class InvestmentRequest(BaseModel):
    stock_count: int
    total_amount: int

# Admin Update Schemas
class ExpenseRequest(BaseModel):
    title: str
    amount: float
    category: str
    phase: int
    date: str  # ISO 8601 string
    notes: Optional[str] = None
    email: str

class GrowthRequest(BaseModel):
    amount: float
    email: str
    date: Optional[str] = None

class ProfitRequest(BaseModel):
    amount: float
    email: str
    date: Optional[str] = None

class PhaseProgressRequest(BaseModel):
    phase1: int
    phase2: int
    phase3: int
    email: str
    date: Optional[str] = None
