"""
Fix LIQUID_ANTIGUEDAD_V2: 2.0 → 2.5 days/month (LOTTT Art. 142 System B).
Applied 2026-06-05. Run once via: python3 scripts/deploy_antiguedad_2_5_fix.py
"""
import xmlrpc.client
import json

cfg = json.load(open('/opt/odoo-dev/config/production.json'))['production']['xmlrpc']
url, db, user, api_key = cfg['url'], cfg['db'], cfg['user'], cfg['api_key']

common = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/common')
uid = common.authenticate(db, user, api_key, {})
models = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/object')

FORMULA = """\
# Antiguedad: 2.5 days per month (LOTTT Art. 142 System B: 30 days/year ÷ 12)
# FIXED 2026-04-08: Relaxed previous_liquidation validation to support terminated+rehired employees
# FIXED 2026-06-05: 2.0 days/month corrected to 2.5 days/month per LOTTT Art. 142 System B (30 days/year)
service_months = LIQUID_SERVICE_MONTHS_V2 or 0.0
antiguedad_daily = LIQUID_ANTIGUEDAD_DAILY_V2 or 0.0

if service_months < 1.03:
    antiguedad_days = 0.0
else:
    try:
        original_hire = contract.ueipab_original_hire_date
        if not original_hire:
            original_hire = False
    except:
        original_hire = False

    try:
        previous_liquidation = contract.ueipab_previous_liquidation_date
        if not previous_liquidation:
            previous_liquidation = False
    except:
        previous_liquidation = False

    if original_hire:
        total_days = (payslip.date_to - original_hire).days
        total_months = total_days / 30.0

        if previous_liquidation and previous_liquidation > original_hire:
            paid_days = (previous_liquidation - original_hire).days
            paid_months = paid_days / 30.0
            net_months = total_months - paid_months
            if net_months > 0:
                antiguedad_days = net_months * 2.5
            else:
                antiguedad_days = 0.0
        else:
            antiguedad_days = total_months * 2.5
    else:
        antiguedad_days = service_months * 2.5

result = antiguedad_days * antiguedad_daily"""

rule = models.execute_kw(db, uid, api_key, 'hr.salary.rule', 'search_read',
    [[('code', '=', 'LIQUID_ANTIGUEDAD_V2')]], {'fields': ['id', 'name'], 'limit': 1})

if not rule:
    print("ERROR: LIQUID_ANTIGUEDAD_V2 not found")
    exit(1)

models.execute_kw(db, uid, api_key, 'hr.salary.rule', 'write',
    [[rule[0]['id']], {'amount_python_compute': FORMULA}])
print(f"LIQUID_ANTIGUEDAD_V2 (id={rule[0]['id']}) updated to 2.5 days/month ✓")
