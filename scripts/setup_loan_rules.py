# -*- coding: utf-8 -*-
"""
setup_loan_rules.py — Idempotent setup for HR Loan salary rules.

Creates VE_LOAN_DED_V2 (quincena) and LIQUID_LOAN_DED_V2 (liquidacion),
links them to their structures, creates LO input types, and patches the
VE_TOTAL_DED_V2 and LIQUID_NET_V2 NET formulas to include the loan block.

Run in testing:
    docker exec -i odoo-dev-web /usr/bin/odoo shell -d testing --no-http \
        < /opt/odoo-dev/scripts/setup_loan_rules.py

Run in production (from prod server):
    docker exec -i ueipab17 /usr/bin/odoo shell -d DB_UEIPAB --no-http \
        < /path/to/setup_loan_rules.py
"""

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def get_account(code):
    acc = env['account.account'].search([('code', '=', code)], limit=1)
    if not acc:
        raise ValueError(f"Account {code} not found — verify chart of accounts")
    return acc

def get_struct(code):
    s = env['hr.payroll.structure'].search([('code', '=', code)], limit=1)
    if not s:
        raise ValueError(f"Payroll structure '{code}' not found")
    return s

def ensure_lo_input(rule):
    """Add LO input type to rule if not already present."""
    existing = rule.input_ids.filtered(lambda i: i.code == 'LO')
    if not existing:
        rule.write({'input_ids': [(0, 0, {'name': 'Loan Recovery', 'code': 'LO'})]})
        print(f"    LO input type added to {rule.code}")
    else:
        print(f"    LO input type already present on {rule.code}")

def ensure_rule_in_struct(rule, struct):
    """Link rule to structure via rule_ids Many2many if not already linked."""
    if rule not in struct.rule_ids:
        struct.write({'rule_ids': [(4, rule.id)]})
        print(f"    Rule {rule.code} linked to structure {struct.code}")
    else:
        print(f"    Rule {rule.code} already in structure {struct.code}")

def patch_formula_if_missing(rule, marker, patch):
    """Append patch block to rule formula only if marker string is absent."""
    current = rule.amount_python_compute or ''
    if marker in current:
        print(f"    Formula of {rule.code} already contains loan block — skipped")
        return
    rule.write({'amount_python_compute': current + patch})
    print(f"    Formula of {rule.code} patched with loan block")

# ---------------------------------------------------------------------------
# Accounts (looked up by code — same IDs in testing and production)
# ---------------------------------------------------------------------------

acc_receivable  = get_account('1.1.06.01.001')   # Cuentas por cobrar empleados
acc_banco       = get_account('1.1.01.02.001')   # Banco Venezuela
acc_prestaciones = get_account('5.1.01.10.010')  # Prestaciones sociales (PD)

print(f"Accounts: receivable={acc_receivable.id}, banco={acc_banco.id}, prestaciones={acc_prestaciones.id}")

# ---------------------------------------------------------------------------
# Structures
# ---------------------------------------------------------------------------

struct_nomina   = get_struct('VE_PAYROLL_V2')
struct_liquid   = get_struct('LIQUID_VE_V2')

print(f"Structures: nomina={struct_nomina.id}, liquidacion={struct_liquid.id}")

# ---------------------------------------------------------------------------
# Rule: VE_LOAN_DED_V2  (quincena — structure VE_PAYROLL_V2, seq 106)
# ---------------------------------------------------------------------------

rule_nomina = env['hr.salary.rule'].search([('code', '=', 'VE_LOAN_DED_V2')], limit=1)
if not rule_nomina:
    rule_nomina = env['hr.salary.rule'].create({
        'name': 'VE_LOAN_DED_V2 - Loan Recovery',
        'code': 'VE_LOAN_DED_V2',
        'sequence': 106,
        'condition_select': 'none',
        'amount_select': 'code',
        'amount_python_compute': 'result = -(inputs.LO.amount) if inputs.LO else 0',
        'account_debit_id': acc_receivable.id,
        'account_credit_id': acc_banco.id,
        'active': True,
    })
    print(f"Created VE_LOAN_DED_V2 (id={rule_nomina.id})")
else:
    rule_nomina.write({
        'sequence': 106,
        'account_debit_id': acc_receivable.id,
        'account_credit_id': acc_banco.id,
        'active': True,
    })
    print(f"VE_LOAN_DED_V2 already exists (id={rule_nomina.id}) — accounts verified")

ensure_lo_input(rule_nomina)
ensure_rule_in_struct(rule_nomina, struct_nomina)

# ---------------------------------------------------------------------------
# Rule: LIQUID_LOAN_DED_V2  (liquidacion — structure LIQUID_VE_V2, seq 196)
# ---------------------------------------------------------------------------

rule_liquid = env['hr.salary.rule'].search([('code', '=', 'LIQUID_LOAN_DED_V2')], limit=1)
if not rule_liquid:
    rule_liquid = env['hr.salary.rule'].create({
        'name': 'LIQUID_LOAN_DED_V2 - Loan Recovery',
        'code': 'LIQUID_LOAN_DED_V2',
        'sequence': 196,
        'condition_select': 'none',
        'amount_select': 'code',
        'amount_python_compute': 'result = -(inputs.LO.amount) if inputs.LO else 0',
        'account_debit_id': acc_receivable.id,
        'account_credit_id': acc_prestaciones.id,
        'active': True,
    })
    print(f"Created LIQUID_LOAN_DED_V2 (id={rule_liquid.id})")
else:
    rule_liquid.write({
        'sequence': 196,
        'account_debit_id': acc_receivable.id,
        'account_credit_id': acc_prestaciones.id,
        'active': True,
    })
    print(f"LIQUID_LOAN_DED_V2 already exists (id={rule_liquid.id}) — accounts verified")

ensure_lo_input(rule_liquid)
ensure_rule_in_struct(rule_liquid, struct_liquid)

# ---------------------------------------------------------------------------
# Patch NET formulas if loan block is missing
# ---------------------------------------------------------------------------

NOMINA_LOAN_PATCH = """
# Loan recovery
try:
    loan = VE_LOAN_DED_V2 or 0
except:
    loan = 0

result = sso + paro + faov + ari + inces + other + loan"""

LIQUID_LOAN_PATCH = """
# Loan recovery deduction
try:
    loan_deduction = LIQUID_LOAN_DED_V2 or 0
except:
    loan_deduction = 0
result = (
    (LIQUID_VACACIONES_V2 or 0) +
    (LIQUID_BONO_VACACIONAL_V2 or 0) +
    (LIQUID_UTILIDADES_V2 or 0) +
    (LIQUID_PRESTACIONES_V2 or 0) +
    (LIQUID_ANTIGUEDAD_V2 or 0) +
    (LIQUID_INTERESES_V2 or 0) +
    (LIQUID_FAOV_V2 or 0) +
    (LIQUID_INCES_V2 or 0) +
    prepaid_deduction +
    loan_deduction
)"""

rule_total_ded = env['hr.salary.rule'].search([('code', '=', 'VE_TOTAL_DED_V2')], limit=1)
if rule_total_ded:
    patch_formula_if_missing(rule_total_ded, 'VE_LOAN_DED_V2', NOMINA_LOAN_PATCH)
else:
    print("WARNING: VE_TOTAL_DED_V2 not found — formula not patched")

rule_liquid_net = env['hr.salary.rule'].search([('code', '=', 'LIQUID_NET_V2')], limit=1)
if rule_liquid_net:
    patch_formula_if_missing(rule_liquid_net, 'LIQUID_LOAN_DED_V2', LIQUID_LOAN_PATCH)
else:
    print("WARNING: LIQUID_NET_V2 not found — formula not patched")

# ---------------------------------------------------------------------------
# Commit
# ---------------------------------------------------------------------------

env.cr.commit()
print("\nsetup_loan_rules.py completed successfully.")
print(f"  VE_LOAN_DED_V2     id={rule_nomina.id}  struct={struct_nomina.code}")
print(f"  LIQUID_LOAN_DED_V2 id={rule_liquid.id}  struct={struct_liquid.code}")
