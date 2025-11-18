#!/usr/bin/env python3
"""
Backup all Liquidation V2 salary rules BEFORE vacation/bono fix
Date: 2025-11-17
Purpose: Create backup for rollback if needed
"""

import json
from datetime import datetime

# Get all LIQUID_VE_V2 structure rules
PayrollStructure = env['hr.payroll.structure']

# Find the LIQUID_VE_V2 structure
structure = PayrollStructure.search([('code', '=', 'LIQUID_VE_V2')], limit=1)
if not structure:
    print("ERROR: LIQUID_VE_V2 structure not found!")
    exit(1)

# Get all rules for this structure (from Many2many relationship)
rules = structure.rule_ids

backup_data = {
    'backup_date': datetime.now().isoformat(),
    'purpose': 'Pre-vacation/bono fix backup for rollback',
    'structure': 'LIQUID_VE_V2',
    'rules_count': len(rules),
    'rules': []
}

print("="*80)
print("LIQUIDATION V2 RULES BACKUP")
print("="*80)
print(f"Structure: LIQUID_VE_V2")
print(f"Total rules: {len(rules)}")
print("="*80)

for rule in rules:
    rule_data = {
        'code': rule.code,
        'name': rule.name,
        'sequence': rule.sequence,
        'category_id': rule.category_id.code if rule.category_id else None,
        'condition_select': rule.condition_select,
        'condition_python': rule.condition_python,
        'amount_select': rule.amount_select,
        'amount_python_compute': rule.amount_python_compute,
        'amount_fix': rule.amount_fix,
        'amount_percentage': rule.amount_percentage,
        'appears_on_payslip': rule.appears_on_payslip,
        'active': rule.active,
    }
    backup_data['rules'].append(rule_data)

    print(f"\n[{rule.sequence}] {rule.code} - {rule.name}")
    print(f"    Category: {rule.category_id.code if rule.category_id else 'N/A'}")
    print(f"    Condition: {rule.condition_select}")
    if rule.amount_select == 'code':
        lines = rule.amount_python_compute.split('\n') if rule.amount_python_compute else []
        print(f"    Formula: {len(lines)} lines")

# Save to JSON file (use /tmp which is writable in container)
backup_file = '/tmp/liquidation_v2_rules_backup_2025-11-17.json'
with open(backup_file, 'w') as f:
    json.dump(backup_data, f, indent=2)

print("\n" + "="*80)
print(f"✅ Backup saved to: {backup_file}")
print("="*80)

# Display the 3 rules we're about to modify
print("\n" + "="*80)
print("RULES TO BE MODIFIED:")
print("="*80)

target_codes = ['LIQUID_VACACIONES_V2', 'LIQUID_BONO_VACACIONAL_V2', 'LIQUID_VACATION_PREPAID_V2']
for code in target_codes:
    rule = rules.filtered(lambda r: r.code == code)
    if rule:
        print(f"\n{code}:")
        print(f"  Name: {rule.name}")
        print(f"  Sequence: {rule.sequence}")
        if rule.amount_python_compute:
            lines = rule.amount_python_compute.split('\n')
            print(f"  Current formula: {len(lines)} lines")
            print(f"  First line: {lines[0][:80]}...")
    else:
        print(f"\n{code}: NOT FOUND!")

print("\n" + "="*80)
