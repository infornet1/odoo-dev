#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Fix template syntax errors caused by sed"""

import re

template_file = '/opt/odoo-dev/addons/ueipab_payroll_enhancements/reports/liquidacion_breakdown_report.xml'

# Read file
with open(template_file, 'r') as f:
    content = f.read()

# Fix all the broken patterns
# Pattern: benefit['key') -> benefit.get('key')
# Pattern: report.get('key') already correct

# Fix: benefit['...')  -> benefit.get('...')
content = re.sub(r"benefit\['([^']+)'\)", r"benefit.get('\1')", content)

# Fix: deduction['...')  -> deduction.get('...')
content = re.sub(r"deduction\['([^']+)'\)", r"deduction.get('\1')", content)

# Fix: report.get('...') - already correct, no change needed

# Write back
with open(template_file, 'w') as f:
    f.write(content)

print("✅ Template syntax fixed!")
print("Fixed patterns:")
print("  - benefit['key') -> benefit.get('key')")
print("  - deduction['key') -> deduction.get('key')")
