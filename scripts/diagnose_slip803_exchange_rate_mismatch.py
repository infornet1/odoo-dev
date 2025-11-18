#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Re-Diagnose SLIP/803 Exchange Rate Mismatch

Relación shows: Bs. 300,621.18
Finiquito shows: Bs. 158,294.80

Different amounts! Let's find out why.
"""

import sys

# Find payslip SLIP/803
payslip = env['hr.payslip'].search([('number', '=', 'SLIP/803')], limit=1)

if not payslip:
    print("ERROR: SLIP/803 not found")
    sys.exit(1)

print("=" * 80)
print("RE-DIAGNOSE: SLIP/803 EXCHANGE RATE MISMATCH")
print("=" * 80)
print(f"Payslip: {payslip.number} - {payslip.employee_id.name}")
print()

print("REPORTED ISSUE:")
print("-" * 80)
print("Relación shows:  Bs. 300,621.18")
print("Finiquito shows: Bs. 158,294.80")
print(f"Difference:      Bs. {300621.18 - 158294.80:,.2f}")
print()

# Get currencies
usd = env.ref('base.USD')
veb = env['res.currency'].search([('name', '=', 'VEB')], limit=1)

# Get net amount in USD
def get_line(code):
    line = payslip.line_ids.filtered(lambda l: l.code == code)
    return line.total if line else 0.0

net_usd = get_line('LIQUID_NET_V2') or get_line('LIQUID_NET')
net_usd = abs(net_usd)

print("NET AMOUNT IN USD:")
print("-" * 80)
print(f"${net_usd:.2f}")
print()

# Calculate what exchange rates would give those amounts
rate_for_relacion = 300621.18 / net_usd if net_usd > 0 else 0
rate_for_finiquito = 158294.80 / net_usd if net_usd > 0 else 0

print("IMPLIED EXCHANGE RATES:")
print("-" * 80)
print(f"Relación:  ${net_usd:.2f} × {rate_for_relacion:.4f} = Bs. 300,621.18")
print(f"Finiquito: ${net_usd:.2f} × {rate_for_finiquito:.4f} = Bs. 158,294.80")
print()

# Check what rates these correspond to
from datetime import date

# Get automatic rate for payslip date (July 31)
rate_rec_july = env['res.currency.rate'].search([
    ('currency_id', '=', veb.id),
    ('name', '<=', payslip.date_to)
], limit=1, order='name desc')
automatic_rate_july = rate_rec_july.company_rate if rate_rec_july and hasattr(rate_rec_july, 'company_rate') else 0.0

# Check Nov 17 rate
rate_rec_nov = env['res.currency.rate'].search([
    ('currency_id', '=', veb.id),
    ('name', '<=', date(2025, 11, 17))
], limit=1, order='name desc')
automatic_rate_nov = rate_rec_nov.company_rate if rate_rec_nov and hasattr(rate_rec_nov, 'company_rate') else 0.0

print("KNOWN EXCHANGE RATES:")
print("-" * 80)
print(f"Automatic rate (Jul 31, 2025):  {automatic_rate_july:.4f}")
print(f"Automatic rate (Nov 17, 2025):  {automatic_rate_nov:.4f}")
print()

# Test both reports with different scenarios
print("=" * 80)
print("SCENARIO 1: NO OVERRIDE (Automatic Jul 31 rate)")
print("=" * 80)
print()

data_no_override = {
    'wizard_id': 1,
    'currency_id': veb.id,
    'currency_name': 'VEB',
    'payslip_ids': [payslip.id],
    'use_custom_rate': False,
    'custom_exchange_rate': None,
    'rate_date': None,
}

relacion_model = env['report.ueipab_payroll_enhancements.liquidacion_breakdown_report']
finiquito_model = env['report.ueipab_payroll_enhancements.finiquito_report']

relacion_result = relacion_model._get_report_values(docids=[payslip.id], data=data_no_override)
relacion_net = relacion_result['reports'][0]['net_amount']

finiquito_result = finiquito_model._get_report_values(docids=[payslip.id], data=data_no_override)
finiquito_net = finiquito_result['reports'][0]['net_amount']

print(f"Relación Net:  Bs. {relacion_net:,.2f}")
print(f"Finiquito Net: Bs. {finiquito_net:,.2f}")
print(f"Match: {abs(relacion_net - finiquito_net) < 1}")
print()

print("=" * 80)
print("SCENARIO 2: WITH OVERRIDE (Nov 17 rate, 236.4601)")
print("=" * 80)
print()

data_with_override = {
    'wizard_id': 1,
    'currency_id': veb.id,
    'currency_name': 'VEB',
    'payslip_ids': [payslip.id],
    'use_custom_rate': True,
    'custom_exchange_rate': 236.4601,
    'rate_date': None,
}

relacion_result_override = relacion_model._get_report_values(docids=[payslip.id], data=data_with_override)
relacion_net_override = relacion_result_override['reports'][0]['net_amount']

finiquito_result_override = finiquito_model._get_report_values(docids=[payslip.id], data=data_with_override)
finiquito_net_override = finiquito_result_override['reports'][0]['net_amount']

print(f"Relación Net:  Bs. {relacion_net_override:,.2f}")
print(f"Finiquito Net: Bs. {finiquito_net_override:,.2f}")
print(f"Match: {abs(relacion_net_override - finiquito_net_override) < 1}")
print()

# Check which scenario matches the reported amounts
print("=" * 80)
print("MATCHING REPORTED AMOUNTS")
print("=" * 80)
print()

print("Relación reported: Bs. 300,621.18")
if abs(relacion_net - 300621.18) < 1:
    print("  ✅ Matches SCENARIO 1 (no override)")
elif abs(relacion_net_override - 300621.18) < 1:
    print("  ✅ Matches SCENARIO 2 (with override)")
else:
    print(f"  ⚠️  Doesn't match either scenario!")
    print(f"     No override:   Bs. {relacion_net:,.2f}")
    print(f"     With override: Bs. {relacion_net_override:,.2f}")

print()

print("Finiquito reported: Bs. 158,294.80")
if abs(finiquito_net - 158294.80) < 1:
    print("  ✅ Matches SCENARIO 1 (no override)")
elif abs(finiquito_net_override - 158294.80) < 1:
    print("  ✅ Matches SCENARIO 2 (with override)")
else:
    print(f"  ⚠️  Doesn't match either scenario!")
    print(f"     No override:   Bs. {finiquito_net:,.2f}")
    print(f"     With override: Bs. {finiquito_net_override:,.2f}")

print()

print("=" * 80)
print("ROOT CAUSE ANALYSIS")
print("=" * 80)
print()

if abs(relacion_net_override - 300621.18) < 1 and abs(finiquito_net - 158294.80) < 1:
    print("🔍 FOUND IT!")
    print()
    print("Relación is using: OVERRIDE rate (236.4601)")
    print("Finiquito is using: AUTOMATIC rate (124.51)")
    print()
    print("This means:")
    print("  1. You generated Relación WITH override checkbox enabled")
    print("  2. You generated Finiquito WITHOUT override (or it's ignoring it)")
    print()
    print("ISSUE: Finiquito may not be reading the override setting correctly!")
    print()
    print("Check wizard settings when you generated both reports:")
    print("  - Was 'Use Custom Exchange Rate' checked?")
    print("  - Did you generate both reports in the same session?")
    print("  - Or did you generate them separately with different settings?")

elif abs(relacion_net - 300621.18) < 1 and abs(finiquito_net_override - 158294.80) < 1:
    print("🔍 Opposite scenario detected!")
    print("(Less likely, but checking...)")

else:
    print("Need more investigation - amounts don't match expected scenarios")

print()

# Check if there's a wizard issue
print("=" * 80)
print("WIZARD VERIFICATION")
print("=" * 80)
print()

print("Please verify when you generated the reports:")
print()
print("For Relación (showing Bs. 300,621.18):")
print("  ☐ Use Custom Exchange Rate: CHECKED or UNCHECKED?")
print("  ☐ Custom Rate Value: _________")
print()
print("For Finiquito (showing Bs. 158,294.80):")
print("  ☐ Use Custom Exchange Rate: CHECKED or UNCHECKED?")
print("  ☐ Custom Rate Value: _________")
print()

print("=" * 80)
print("Analysis complete!")
print("=" * 80)
