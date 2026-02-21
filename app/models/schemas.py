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
    phase1_progress: Optional[int] = 0
    phase2_progress: Optional[int] = 0
    phase3_progress: Optional[int] = 0

class AllocationItem(BaseModel):
    name: str
    value: int

# Invest Schemas
class InvestmentRequest(BaseModel):
    stock_count: int
    total_amount: int
    email: str
    fund_id: Optional[str] = None

# Admin Update Schemas
class ExpenseRequest(BaseModel):
    title: str
    amount: float
    category: str
    phase: int
    date: Optional[str] = None
    notes: Optional[str] = None
    email: str
    fund_id: str

class GrowthRequest(BaseModel):
    amount: float
    email: str
    date: Optional[str] = None
    fund_id: str

class ProfitRequest(BaseModel):
    amount: float
    email: str
    date: Optional[str] = None
    fund_id: str

class PhaseProgressRequest(BaseModel):
    phase1: int
    phase2: int
    phase3: int
    email: str
    date: Optional[str] = None
    fund_id: str

class ARRItem(BaseModel):
    year: str
    growth_rate: float

class ARRBulkUpdateRequest(BaseModel):
    updates: List[ARRItem]
    email: str
    fund_id: str

class RoadmapStep(BaseModel):
    phase: str
    date: str
    status: str

class RoadmapUpdateRequest(BaseModel):
    roadmap: List[RoadmapStep]
    email: str
    fund_id: str

class FundDatesUpdateRequest(BaseModel):
    entry_date: str
    exit_date: str
    p1_start_date: Optional[str] = None
    p1_end_date: Optional[str] = None
    p2_start_date: Optional[str] = None
    p2_end_date: Optional[str] = None
    p3_start_date: Optional[str] = None
    p3_end_date: Optional[str] = None
    email: str
    fund_id: str

class ManagerCreateRequest(BaseModel):
    name: str
    email: str
    phone: str
    assigned_fund: Optional[str] = None
    ceo_email: str

class FundCreateRequest(BaseModel):
    name: str
    location: str
    target_amount: float
    total_stocks: int
    stock_price: float
    entry_date: str
    exit_date: str
    phase: str
    land_value: Optional[float] = 0
    description: Optional[str] = None
    blueprint_url: Optional[str] = None
    ceo_email: str
