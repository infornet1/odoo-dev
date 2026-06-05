"""
Deploy VE_PERIOD_RATIO_V2 rule and updated NOMINA_VE_V2 salary rule formulas to production.
Run once via: python3 scripts/deploy_ve_period_ratio_prod.py
"""
import xmlrpc.client
import json

cfg = json.load(open('/opt/odoo-dev/config/production.json'))['production']['xmlrpc']
url, db, user, api_key = cfg['url'], cfg['db'], cfg['user'], cfg['api_key']

common = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/common')
uid = common.authenticate(db, user, api_key, {})
models = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/object')
print(f"Connected as uid={uid}")

def search(model, domain, fields=None, limit=1):
    return models.execute_kw(db, uid, api_key, model, 'search_read', [domain],
                             {'fields': fields or ['id', 'name'], 'limit': limit})

def write(model, ids, vals):
    return models.execute_kw(db, uid, api_key, model, 'write', [ids, vals])

def create(model, vals):
    return models.execute_kw(db, uid, api_key, model, 'create', [vals])

# ── Locate NOMINA_VE_V2 structure ─────────────────────────────────────────────
struct = search('hr.payroll.structure', [('code', '=', 'VE_PAYROLL_V2')], ['id', 'name'])
if not struct:
    print("ERROR: VE_PAYROLL_V2 structure not found in production")
    exit(1)
struct_id = struct[0]['id']
print(f"Structure: {struct[0]['name']} (id={struct_id})")

# ── VE_PERIOD_RATIO_V2 rule ───────────────────────────────────────────────────
RATIO_FORMULA = """\
try:
    is_partial = payslip.dict.is_partial_quincena
except:
    is_partial = False

if is_partial:
    period_days = (payslip.date_to - payslip.date_from).days + 1
    result = period_days / 15.0
else:
    result = 1.0"""

existing = search('hr.salary.rule', [('code', '=', 'VE_PERIOD_RATIO_V2')], ['id', 'name'])
if existing:
    write('hr.salary.rule', [existing[0]['id']], {'amount_python_compute': RATIO_FORMULA})
    print(f"VE_PERIOD_RATIO_V2 updated (id={existing[0]['id']})")
else:
    basic_cat = search('hr.salary.rule.category', [('code', '=', 'BASIC')], ['id'])
    new_id = create('hr.salary.rule', {
        'name': 'Ratio Período (helper)',
        'code': 'VE_PERIOD_RATIO_V2',
        'sequence': 0,
        'category_id': basic_cat[0]['id'],
        'condition_select': 'none',
        'amount_select': 'code',
        'amount_python_compute': RATIO_FORMULA,
        'active': True,
    })
    models.execute_kw(db, uid, api_key, 'hr.payroll.structure', 'write',
                      [[struct_id], {'rule_ids': [(4, new_id)]}])
    print(f"VE_PERIOD_RATIO_V2 created (id={new_id}) and linked to structure")

# ── Update 9 existing rules ───────────────────────────────────────────────────
RULES = {
    'VE_SALARY_V2': """\
monthly_salary = contract.ueipab_salary_v2 or 0.0
multiplier = VE_PERIOD_RATIO_V2 or 1.0
if payslip.payslip_run_id and (payslip.payslip_run_id.is_advance_payment or payslip.payslip_run_id.is_remainder_batch):
    multiplier = (payslip.payslip_run_id.advance_percentage or 100.0) / 100.0
result = (monthly_salary / 2.0) * multiplier""",

    'VE_EXTRABONUS_V2': """\
monthly_extrabonus = contract.ueipab_extrabonus_v2 or 0.0
multiplier = VE_PERIOD_RATIO_V2 or 1.0
if payslip.payslip_run_id and (payslip.payslip_run_id.is_advance_payment or payslip.payslip_run_id.is_remainder_batch):
    multiplier = (payslip.payslip_run_id.advance_percentage or 100.0) / 100.0
result = (monthly_extrabonus / 2.0) * multiplier""",

    'VE_BONUS_V2': """\
monthly_bonus = contract.ueipab_bonus_v2 or 0.0
multiplier = VE_PERIOD_RATIO_V2 or 1.0
if payslip.payslip_run_id and (payslip.payslip_run_id.is_advance_payment or payslip.payslip_run_id.is_remainder_batch):
    multiplier = (payslip.payslip_run_id.advance_percentage or 100.0) / 100.0
result = (monthly_bonus / 2.0) * multiplier""",

    'VE_CESTA_TICKET_V2': """\
monthly_cesta = contract.cesta_ticket_usd or 0.0
result = (monthly_cesta / 2.0) * (VE_PERIOD_RATIO_V2 or 1.0)""",

    'VE_SSO_DED_V2': """\
sso_ceiling_bs = 1300.0
exchange_rate = payslip.exchange_rate_used or 236.4601
sso_ceiling_usd = sso_ceiling_bs / exchange_rate
employee_salary_usd = contract.ueipab_salary_v2 or 0.0
sso_base = min(employee_salary_usd, sso_ceiling_usd)
monthly_deduction = sso_base * 0.04
result = -(monthly_deduction / 2.0) * (VE_PERIOD_RATIO_V2 or 1.0)""",

    'VE_PARO_DED_V2': """\
monthly_salary = contract.ueipab_salary_v2 or 0.0
monthly_deduction = monthly_salary * 0.005
result = -(monthly_deduction / 2.0) * (VE_PERIOD_RATIO_V2 or 1.0)""",

    'VE_FAOV_DED_V2': """\
monthly_salary = contract.ueipab_salary_v2 or 0.0
monthly_deduction = monthly_salary * 0.01
result = -(monthly_deduction / 2.0) * (VE_PERIOD_RATIO_V2 or 1.0)""",

    'VE_ARI_DED_V2': """\
monthly_salary = contract.ueipab_salary_v2 or 0.0
ari_rate = (contract.ueipab_ari_withholding_rate or 0.0) / 100.0
monthly_deduction = monthly_salary * ari_rate
result = -(monthly_deduction / 2.0) * (VE_PERIOD_RATIO_V2 or 1.0)""",

    'VE_OTHER_DED_V2': """\
monthly_amount = contract.ueipab_other_deductions or 0.0
result = -(monthly_amount / 2.0) * (VE_PERIOD_RATIO_V2 or 1.0)""",
}

for code, formula in RULES.items():
    rule = search('hr.salary.rule', [('code', '=', code)], ['id', 'name'])
    if rule:
        write('hr.salary.rule', [rule[0]['id']], {'amount_python_compute': formula})
        print(f"  {code:<25} updated (id={rule[0]['id']})")
    else:
        print(f"  {code:<25} NOT FOUND — skipped")

print("\nDone — production salary rules updated.")
