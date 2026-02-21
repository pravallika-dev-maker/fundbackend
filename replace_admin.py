import re

with open('app/routes/admin.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Endpoints whose check_ceo should become check_authorized (fund operations)
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
    # Pattern: inside the function body, the first check_ceo call
    pattern = rf'(async def {func_name}\(.*?\):\r?\n\s+try:\r?\n\s+)check_ceo\(req\.email\)'
    replacement = rf'\1check_authorized(req.email, req.fund_id)'
    new_content = re.sub(pattern, replacement, content, count=1, flags=re.DOTALL)
    if new_content != content:
        content = new_content
        print(f'Replaced check_ceo -> check_authorized in {func_name}')
    else:
        print(f'WARNING: No match found for {func_name}')

with open('app/routes/admin.py', 'w', encoding='utf-8') as f:
    f.write(content)

print('Done.')
