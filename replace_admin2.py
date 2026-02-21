with open('app/routes/admin.py', 'rb') as f:
    raw = f.read()

content = raw.decode('utf-8')

# Fund-operation functions that should allow fund managers too
fund_ops = [
    'add_expense',
    'update_growth',
    'add_profit',
    'update_phase',
    'update_arr',
    'update_roadmap',
    'update_fund_dates',
]

for func_name in fund_ops:
    func_header = f'async def {func_name}('
    idx = content.find(func_header)
    if idx == -1:
        print(f'WARNING: Function not found: {func_name}')
        continue

    # Find check_ceo after this position
    check_old = 'check_ceo(req.email)'
    check_new = 'check_authorized(req.email, req.fund_id)'
    check_idx = content.find(check_old, idx)
    if check_idx == -1:
        print(f'WARNING: check_ceo not found in {func_name}')
        continue

    # Make sure we don't cross into another function
    next_func_idx = content.find('\n@router.', idx + 1)
    if next_func_idx != -1 and check_idx > next_func_idx:
        print(f'WARNING: check_ceo found outside {func_name} scope')
        continue

    content = content[:check_idx] + check_new + content[check_idx + len(check_old):]
    print(f'OK: {func_name}')

with open('app/routes/admin.py', 'wb') as f:
    f.write(content.encode('utf-8'))

print('All done.')
