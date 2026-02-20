from fastapi import APIRouter, HTTPException
from app.utils.supabase import supabase

router = APIRouter()

@router.get("/")
async def get_portfolio(email: str):
    try:
        # 1. Get profile
        profile_res = supabase.table('profiles').select("*").eq('email', email).single().execute()
        if not profile_res.data:
            raise HTTPException(status_code=404, detail="Profile not found")
        profile = profile_res.data
            
        # 2. Get all investments for this user
        invest_res = supabase.table('investments')\
            .select("*, funds(name)")\
            .eq('email', email)\
            .order('created_at', desc=False)\
            .execute()
        
        investments = invest_res.data or []
        
        # 3. Aggregate holdings by Fund
        holdings_map = {}
        for inv in investments:
            fid = inv['fund_id']
            fname = inv.get('funds', {}).get('name', 'Unknown Fund') if inv.get('funds') else 'Unknown Fund'
            if fid not in holdings_map:
                # Get latest price for this specific fund
                price_res = supabase.table('fund_metrics').select("stock_price").eq('fund_id', fid).order('id', desc=True).limit(1).execute()
                price = price_res.data[0]['stock_price'] if price_res.data else 26500
                holdings_map[fid] = {
                    "fund_id": fid,
                    "name": fname,
                    "units": 0,
                    "current_price": price,
                    "invested_amount": 0
                }
            holdings_map[fid]["units"] += inv['stock_count']
            holdings_map[fid]["invested_amount"] += inv['amount_paid']

        holdings = list(holdings_map.values())
        for h in holdings:
            h["current_value"] = h["units"] * h["current_price"]

        # 4. Create multi-fund growth timeline
        # We want data points per date where we see total value and per-fund value
        timeline_map = {}
        running_fund_totals = {fid: 0 for fid in holdings_map.keys()}
        
        for inv in investments:
            fid = inv['fund_id']
            date_key = inv['created_at'][:10] # YYYY-MM-DD
            running_fund_totals[fid] += inv['stock_count']
            
            # Calculate total value at this point in time
            total_val = 0
            fund_values = {}
            for f_id, f_units in running_fund_totals.items():
                f_price = holdings_map[f_id]["current_price"] # Simple fix: use current price for all points
                val = f_units * f_price
                total_val += val
                fund_values[holdings_map[f_id]["name"]] = val
            
            timeline_map[date_key] = {
                "date": date_key,
                "total": total_val,
                **fund_values
            }

        sorted_timeline = sorted(timeline_map.values(), key=lambda x: x['date'])

        return {
            "is_investor": profile.get('is_investor', False),
            "total_stocks": profile.get('total_stocks', 0) or 0,
            "total_portfolio_value": sum(h["current_value"] for h in holdings),
            "holdings": holdings,
            "history": investments[::-1], # Recent first
            "timeline": sorted_timeline,
            "fund_names": [h["name"] for h in holdings]
        }
    except Exception as e:
        print(f"Error in get_portfolio: {e}")
        raise HTTPException(status_code=500, detail=str(e))
