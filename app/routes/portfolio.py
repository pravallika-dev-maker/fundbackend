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
            status = inv.get('status', 'completed')
            
            if fid not in holdings_map:
                # Get latest price for this specific fund
                price_res = supabase.table('fund_metrics').select("stock_price, land_value, total_profits")\
                    .eq('fund_id', fid).order('id', desc=True).limit(1).execute()
                
                # Dynamic valuation logic
                fund_res = supabase.table('funds').select('target_amount').eq('id', fid).single().execute()
                target = float(fund_res.data.get('target_amount') or 0)
                
                land = 0
                profits = 0
                if price_res.data:
                    land = float(price_res.data[0].get('land_value') or 0)
                    profits = float(price_res.data[0].get('total_profits') or 0)
                
                # Current Price based on institutional valuation
                current_price = int((target + land + profits) / 1000) if target > 0 else 26500
                
                holdings_map[fid] = {
                    "fund_id": fid,
                    "name": fname,
                    "units": 0,
                    "current_price": current_price,
                    "invested_amount": 0,
                    "status": "Active" if status == 'completed' else "Pending Allocation",
                    "valuation": 0
                }
            
            # Aggregate units and invested amount
            holdings_map[fid]["units"] += inv['stock_count']
            holdings_map[fid]["invested_amount"] += inv['amount_paid']
            if status != 'completed':
                holdings_map[fid]["status"] = "Pending Allocation"

        holdings = list(holdings_map.values())
        for h in holdings:
            h["current_value"] = h["units"] * h["current_price"]
            h["avg_price"] = h["invested_amount"] / h["units"] if h["units"] > 0 else 0
            
            # Fetch specific annual growth rate from metrics
            fm_res = supabase.table('fund_metrics').select("growth_percentage")\
                .eq('fund_id', h["fund_id"]).order('id', desc=True).limit(1).execute()
            h["annual_growth"] = fm_res.data[0].get('growth_percentage', 12.5) if (fm_res.data and len(fm_res.data) > 0) else 12.5

        # 4. Create multi-fund growth timeline
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
                f_price = holdings_map[f_id]["current_price"]
                val = f_units * f_price
                total_val += val
                fund_values[holdings_map[f_id]["name"]] = val
            
            timeline_map[date_key] = {
                "date": date_key,
                "total": total_val,
                **fund_values
            }

        sorted_timeline = sorted(timeline_map.values(), key=lambda x: x['date'])

        # Correctly determine investor status
        is_investor = profile.get('is_investor', False) or len(holdings) > 0

        return {
            "is_investor": is_investor,
            "total_stocks": sum(h["units"] for h in holdings),
            "total_portfolio_value": sum(h["current_value"] for h in holdings),
            "holdings": holdings,
            "history": investments[::-1],
            "timeline": sorted_timeline,
            "fund_names": [h["name"] for h in holdings]
        }
    except Exception as e:
        print(f"Error in get_portfolio: {e}")
        raise HTTPException(status_code=500, detail=str(e))
