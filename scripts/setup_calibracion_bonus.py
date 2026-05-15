#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Setup script: BONO_CALIBRACION salary rule in NOMINA_VE_V2 structure.

Run via:
    docker exec -i odoo-dev-web /usr/bin/odoo shell -d testing --no-http \
        < /opt/odoo-dev/scripts/setup_calibracion_bonus.py

What this script does:
    1. Locates the VE_PAYROLL_V2 payroll structure (NOMINA_VE_V2).
    2. Checks whether the BONO_CALIBRACION rule already exists (idempotent).
    3. Creates the salary rule with:
         - category: ALW (Allowance) — same as other bonus earnings rules
         - sequence: 6 (after VE_CESTA_TICKET_V2 at seq=4, before VE_GROSS_V2 at seq=5)
           NOTE: sequence must be < 5 to be summed into GROSS, OR > 5 but the
           GROSS rule uses categories.ALW. We use sequence=6 and place it AFTER
           the GROSS aggregator would see it — but since GROSS sums category ALW,
           BONO_CALIBRACION (also ALW) will be included automatically.
           Actually: sequence=6 comes after seq=5 (GROSS). To be included in GROSS,
           we need sequence < 5. Use sequence=4 is taken. Let us use sequence=45
           and category=ALW — GROSS aggregates at seq=5 so BONO_CALIBRACION at
           seq=45 would be AFTER GROSS. Safe approach: use a separate BONUS
           category or keep as ALW and note that GROSS will NOT include it.

           FINAL DECISION: use sequence=6, category=ALW. The GROSS rule (seq=5)
           aggregates all ALW rules already processed (seq <= 5). Since our rule
           runs at seq=6 (after GROSS), it WON'T be counted in GROSS or VE_NET_V2.
           Instead, we pattern it like BONO_MADRES: NET rule handles the final
           NET amount. But for V2 batches, VE_NET_V2 = categories.BASIC + ...

           CORRECT APPROACH (matching existing bonus patterns):
           - Sequence=45 so it runs BEFORE VE_GROSS_V2 (seq=5)? No, seq=5 < 45.
           - Look at actual existing rules: BONO_MADRES structure has its own NET rule.
           - For NOMINA_VE_V2, VE_NET_V2 = GROSS - DED total. GROSS = sum(ALW).
           - To be in GROSS → category must be ALW AND sequence < seq of VE_GROSS_V2.
           - VE_GROSS_V2 is at sequence=5. All current ALW rules are seq 1-4.
           - So sequence must be <= 4 to appear before GROSS, OR we need a different approach.

           SIMPLEST CORRECT APPROACH: sequence=4 is taken by VE_CESTA_TICKET_V2.
           Use sequence=4 with a higher sub-sequence isn't possible in Odoo.
           Use sequence=45 with category=ALW: the GROSS aggregator at seq=5 runs
           BEFORE this rule, so categories.ALW at GROSS time won't include it.

           PRODUCTION PATTERN: Set sequence=3 (between VE_BONUS_V2=3 and
           VE_CESTA_TICKET_V2=4)? Both rules share sequence=3 and 4 respectively.

           BEST SOLUTION: Use sequence=45 and handle NET contribution explicitly
           by including in category ALW (VE_NET_V2 uses categories.NET which is
           computed from categories.GROSS - categories.DED).

           RE-READING VE_NET_V2: let's check the actual formula first.
    4. Reports what was created.

Note: After running, open a draft payslip in a V2 batch, add a CALIBRACION_GLENDA
input with amount > 0, then recompute the payslip to see BONO_CALIBRACION appear.
"""

import sys

# ============================================================
# Step 0: Verify we are on the correct database
# ============================================================
active_db = env['ir.config_parameter'].sudo().get_param('ai_agent.active_db', '')
db_name = env.cr.dbname
print(f"Connected to database: {db_name!r}  (active_db param: {active_db!r})")
if db_name not in ('testing', 'testing_backup'):
    print(f"ERROR: This script is intended for the testing database, not {db_name!r}.")
    print("Aborting — no changes made.")
    sys.exit(1)

# ============================================================
# Step 1: Check VE_NET_V2 formula to understand how NET works
# ============================================================
net_rule = env['hr.salary.rule'].search([('code', '=', 'VE_NET_V2')], limit=1)
if net_rule:
    print(f"\nVE_NET_V2 (seq={net_rule.sequence}):")
    print(f"  amount_select: {net_rule.amount_select}")
    print(f"  amount_python_compute: {net_rule.amount_python_compute!r}")
else:
    print("WARNING: VE_NET_V2 not found — cannot verify NET formula")

# Check VE_GROSS_V2 as well
gross_rule = env['hr.salary.rule'].search([('code', '=', 'VE_GROSS_V2')], limit=1)
if gross_rule:
    print(f"\nVE_GROSS_V2 (seq={gross_rule.sequence}):")
    print(f"  amount_select: {gross_rule.amount_select}")
    print(f"  amount_python_compute: {gross_rule.amount_python_compute!r}")

# ============================================================
# Step 2: Locate the VE_PAYROLL_V2 structure
# ============================================================
struct = env['hr.payroll.structure'].search([('code', '=', 'VE_PAYROLL_V2')], limit=1)
if not struct:
    print("\nERROR: Payroll structure 'VE_PAYROLL_V2' not found.")
    print("Is the NOMINA_VE_V2 structure installed in this database?")
    sys.exit(1)

print(f"\nFound structure: {struct.name!r} (id={struct.id}, code={struct.code})")

# Print current rule sequences to determine correct placement
print("\nExisting rules in structure (ordered by sequence):")
for r in struct.rule_ids.sorted('sequence'):
    print(f"  seq={r.sequence:3d} | {r.code:30s} | cat={r.category_id.code:6s} | {r.name}")

# ============================================================
# Step 3: Check idempotency — does rule already exist?
# ============================================================
existing = env['hr.salary.rule'].search([('code', '=', 'BONO_CALIBRACION')], limit=1)
if existing:
    print(f"\nBONO_CALIBRACION rule already exists (id={existing.id}).")
    print(f"  Sequence: {existing.sequence}")
    print(f"  Category: {existing.category_id.code}")
    print(f"  Condition: {existing.condition_select}")
    print(f"  In structures: {[s.name for s in existing.struct_id]}")
    # Check if it's in the V2 structure via many2many
    if struct in existing.struct_id:
        print(f"  Already linked to {struct.name} — nothing to do.")
    else:
        struct.write({'rule_ids': [(4, existing.id)]})
        print(f"  Linked to {struct.name}.")
    env.cr.commit()
    sys.exit(0)

# ============================================================
# Step 4: Look up ALW category
# ============================================================
cat_alw = env['hr.salary.rule.category'].search([('code', '=', 'ALW')], limit=1)
if not cat_alw:
    print("\nERROR: Salary rule category 'ALW' not found.")
    sys.exit(1)
print(f"\nAllowance category: id={cat_alw.id}, code={cat_alw.code}")

# ============================================================
# Step 5: Determine correct sequence
# ============================================================
# VE_GROSS_V2 is at sequence 5. The GROSS rule aggregates categories.ALW
# at the moment it runs. Rules with sequence > 5 that use category ALW
# will NOT be included in GROSS because GROSS has already executed.
#
# VE_NET_V2 uses: result = categories.GROSS - categories.DED (or similar).
# If BONO_CALIBRACION is ALW but runs after GROSS, it's not in GROSS.
# Therefore it's also not in NET. We need one of:
#   A) sequence < 5 (runs before GROSS) — gets into GROSS → NET automatically
#   B) sequence > 200 (runs after NET) — add its own accounting, like BONO_MADRES_NET
#
# Option A is cleaner for a V2 batch bonus (it rolls up normally).
# VE_CESTA_TICKET_V2 is at seq=4, VE_BONUS_V2 at seq=3.
# We can use seq=4 only if it's a different rule — Odoo allows duplicate sequences
# (they sort by sequence, then by id). Using seq=4 is fine; Odoo processes ties by id.
# But to be explicit and avoid ambiguity, use seq=3 (ties with VE_BONUS_V2).
# Actually cleanest: use seq=48, place it BETWEEN earnings and before GROSS.
# Wait — GROSS is at seq=5. Any rule with seq < 5 runs before GROSS.
# seq=4 is VE_CESTA_TICKET_V2 — use 4 and let natural id ordering break the tie.
# Even cleaner: use seq=4 with a comment. Odoo does not deduplicate sequences.
#
# FINAL: use sequence=4 (runs right before GROSS at seq=5).
# This ensures the calibration bonus IS included in GROSS → NET → disbursement.

RULE_SEQUENCE = 4  # Before VE_GROSS_V2 (seq=5); ties with VE_CESTA_TICKET_V2 are OK

# ============================================================
# Step 6: Create the BONO_CALIBRACION salary rule
# ============================================================
# Condition: only fires when a CALIBRACION_GLENDA input exists with amount > 0
# Using payslip.dict to access the actual hr.payslip record and its input_line_ids.
# This mirrors the pattern used in VE_LOAN_DED_V2.
# NOTE: condition_select must be 'none' (not 'python') so the rule always runs and always
# seeds localdict with BONO_CALIBRACION = 0.  If condition_select='python' and an employee
# has no CALIBRACION_GLENDA input, the rule is skipped → BONO_CALIBRACION absent from
# localdict → VE_NET_V2 raises NameError → "Wrong python code defined" error.
CONDITION_PYTHON = (
    "slip = payslip.dict\n"
    "result = sum(l.amount for l in slip.input_line_ids if l.code == 'CALIBRACION_GLENDA') > 0"
)

# Formula: sessions × (monthly_salary / 21.75)
# inputs.CALIBRACION_GLENDA would return 0.0 (float) if missing because BrowsableObject
# __getattr__ returns 0.0 for absent keys — not a record object.
# Safe pattern: access via payslip.dict.input_line_ids directly.
AMOUNT_PYTHON = (
    "slip = payslip.dict\n"
    "sessions = sum(l.amount for l in slip.input_line_ids if l.code == 'CALIBRACION_GLENDA')\n"
    "monthly = contract.wage or 0.0\n"
    "result = sessions * (monthly / 21.75)"
)

rule_vals = {
    'name': 'Bono Calibración Glenda',
    'code': 'BONO_CALIBRACION',
    'category_id': cat_alw.id,
    'sequence': RULE_SEQUENCE,
    'condition_select': 'none',   # must be 'none' — see comment above CONDITION_PYTHON
    'condition_python': CONDITION_PYTHON,
    'amount_select': 'code',
    'amount_python_compute': AMOUNT_PYTHON,
    'appears_on_payslip': True,
    'active': True,
    # No account_debit / account_credit: earnings rules do NOT post to accounting.
    # Only NET and deduction rules post journal entries in this pattern.
}

new_rule = env['hr.salary.rule'].create(rule_vals)
print(f"\nCreated salary rule: {new_rule.name!r} (id={new_rule.id}, code={new_rule.code})")
print(f"  Sequence: {new_rule.sequence}")
print(f"  Category: {new_rule.category_id.code} ({new_rule.category_id.name})")
print(f"  Condition: {new_rule.condition_select}")
print(f"  Appears on payslip: {new_rule.appears_on_payslip}")

# ============================================================
# Step 7: Link rule to the VE_PAYROLL_V2 structure (many2many)
# ============================================================
# hr.payroll.structure.rule_ids is a many2many in hr_payroll_community.
# Use the (4, id) ORM command to add without removing existing rules.
struct.write({'rule_ids': [(4, new_rule.id)]})
print(f"\nLinked BONO_CALIBRACION to structure: {struct.name!r}")

# ============================================================
# Step 8: Update VE_NET_V2 to include BONO_CALIBRACION
# ============================================================
# Design decision: BONO_CALIBRACION is a bonus NOT subject to social
# deductions (SSO/FAOV/PARO). It is added directly to NET, bypassing
# GROSS. This mirrors Venezuelan practice for non-deductible bonuses.
#
# VE_GROSS_V2 is hardcoded: result = VE_SALARY_V2 + VE_EXTRABONUS_V2 + ...
# VE_NET_V2 is:              result = VE_GROSS_V2 + VE_TOTAL_DED_V2
#
# We extend VE_NET_V2 to: result = VE_GROSS_V2 + VE_TOTAL_DED_V2 + BONO_CALIBRACION
# The rules BrowsableObject.__getattr__ returns 0.0 for keys not in rules_dict,
# so BONO_CALIBRACION evaluates to 0.0 when the condition rule was not satisfied.
net_rule = env['hr.salary.rule'].search([('code', '=', 'VE_NET_V2')], limit=1)
if not net_rule:
    print("WARNING: VE_NET_V2 not found — cannot update NET formula. Manual action required.")
else:
    current_net_formula = net_rule.amount_python_compute
    if 'BONO_CALIBRACION' in current_net_formula:
        print(f"\nVE_NET_V2 already includes BONO_CALIBRACION — skipping formula update.")
    else:
        new_net_formula = 'result = VE_GROSS_V2 + VE_TOTAL_DED_V2 + BONO_CALIBRACION'
        net_rule.write({'amount_python_compute': new_net_formula})
        print(f"\nUpdated VE_NET_V2 formula:")
        print(f"  Before: {current_net_formula!r}")
        print(f"  After:  {new_net_formula!r}")

# ============================================================
# Step 9: Commit and verify
# ============================================================
env.cr.commit()
print("\nCommitted successfully.")

# Verify final state
print("\nFinal rules in structure (ordered by sequence):")
for r in struct.rule_ids.sorted('sequence'):
    marker = " <-- NEW" if r.code == 'BONO_CALIBRACION' else ""
    print(f"  seq={r.sequence:3d} | {r.code:30s} | cat={r.category_id.code:6s}{marker}")

print("\nSetup complete.")
print("\nNext steps:")
print("  1. The module is already upgraded (wizard is live).")
print("  2. In a V2 (NOMINA_VE_V2) batch, open a draft payslip.")
print("  3. Add an input line: code=CALIBRACION_GLENDA, amount=<session_count>.")
print("  4. Click 'Recompute'. You should see BONO_CALIBRACION appear.")
print("  5. Alternatively, use 'Bonos Calibración Glenda' button on the batch form.")
