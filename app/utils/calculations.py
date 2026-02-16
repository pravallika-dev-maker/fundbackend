from typing import List, Dict, Any
from datetime import datetime
from collections import defaultdict

def get_daily_expenses(expenses: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Group by day (YYYY-MM-DD) and sum amount."""
    grouped = defaultdict(float)
    for exp in expenses:
        date_str = exp['date'].split('T')[0] if 'T' in exp['date'] else exp['date'][:10]
        grouped[date_str] += float(exp['amount'])
    
    return [{"label": k, "total": v} for k, v in sorted(grouped.items())]

def get_monthly_expenses(expenses: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Group by month (YYYY-MM) and sum amount."""
    grouped = defaultdict(float)
    for exp in expenses:
        # parsed_date = datetime.fromisoformat(exp['date'].replace('Z', '+00:00'))
        # month_str = parsed_date.strftime('%Y-%m') # Or just string slice if consistent ISO
        date_str = exp['date']
        month_str = date_str[:7] # YYYY-MM
        grouped[month_str] += float(exp['amount'])
        
    return [{"label": k, "total": v} for k, v in sorted(grouped.items())]

def get_yearly_expenses(expenses: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Group by year (YYYY) and sum amount."""
    grouped = defaultdict(float)
    for exp in expenses:
        date_str = exp['date']
        year_str = date_str[:4] # YYYY
        grouped[year_str] += float(exp['amount'])
        
    return [{"label": k, "total": v} for k, v in sorted(grouped.items())]

def get_phase_wise_expenses(expenses: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Group by phase and sum amount."""
    grouped = defaultdict(float)
    for exp in expenses:
        phase = str(exp['phase'])
        grouped[f"Phase {phase}"] += float(exp['amount'])
        
    return [{"label": k, "total": v} for k, v in sorted(grouped.items())]

def get_category_wise_expenses(expenses: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Group by category and sum amount."""
    grouped = defaultdict(float)
    for exp in expenses:
        cat = exp['category']
        grouped[cat] += float(exp['amount'])
        
    return [{"label": k, "total": v} for k, v in sorted(grouped.items())]

def get_monthly_category_breakdown(expenses: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Group by month and then by category.
    Returns: [{ "month": "2023-01", "Infrastructure": 5000, "Travel": 200, "total": 5200 }, ...]
    """
    grouped = defaultdict(lambda: defaultdict(float))
    all_categories = set()
    
    for exp in expenses:
        date_str = exp['date']
        month_str = date_str[:7] # YYYY-MM
        cat = exp['category']
        amount = float(exp['amount'])
        
        grouped[month_str][cat] += amount
        grouped[month_str]['total'] += amount
        all_categories.add(cat)
    
    result = []
    # If no expenses, return empty
    if not grouped:
        return []
        
    for month, cats in sorted(grouped.items()):
        entry = {"month": month, "total": cats['total']}
        for cat in all_categories:
            entry[cat] = cats.get(cat, 0)
        result.append(entry)
        
    return result
