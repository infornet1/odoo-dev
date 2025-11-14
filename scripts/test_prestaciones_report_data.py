#!/usr/bin/env python3
"""
Test Prestaciones Interest Report Data Generation
==================================================

Test if the report model is generating data correctly.

Author: Claude Code
Date: 2025-11-13
"""

print("="*80)
print("TESTING PRESTACIONES INTEREST REPORT DATA")
print("="*80)
print()

# Find a liquidation payslip to test
Payslip = env['hr.payslip']
payslip = Payslip.search([
    ('struct_id.name', '=', 'Liquidación Venezolana'),
    ('state', 'in', ['draft', 'done'])
], limit=1)

if not payslip:
    print("❌ No liquidation payslips found!")
    import sys
    sys.exit(1)

print(f"✅ Testing with payslip: {payslip.number}")
print(f"   Employee: {payslip.employee_id.name}")
print(f"   State: {payslip.state}")
print(f"   Date: {payslip.date_from} to {payslip.date_to}")
print()

# Get the report model
try:
    report_model = env['report.ueipab_payroll_enhancements.prestaciones_interest']
    print(f"✅ Report Model found: {report_model._name}")
except Exception as e:
    print(f"❌ Report Model ERROR: {e}")
    import sys
    sys.exit(1)

print()

# Test _get_report_values
print("Testing _get_report_values()...")
print()

Currency = env['res.currency']
usd = Currency.search([('name', '=', 'USD')], limit=1)

data = {
    'currency_id': usd.id,
    'currency_name': 'USD',
    'payslip_ids': [payslip.id],
}

try:
    result = report_model._get_report_values(docids=[payslip.id], data=data)

    print("✅ _get_report_values() returned:")
    print(f"   doc_ids: {result.get('doc_ids')}")
    print(f"   doc_model: {result.get('doc_model')}")
    print(f"   docs: {result.get('docs')}")
    print(f"   currency: {result.get('currency').name if result.get('currency') else 'None'}")
    print(f"   reports count: {len(result.get('reports', []))}")
    print()

    if result.get('reports'):
        first_report = result['reports'][0]
        print("First Report Data:")
        print(f"   Employee: {first_report.get('employee').name if first_report.get('employee') else 'None'}")
        print(f"   Contract: {first_report.get('contract').name if first_report.get('contract') else 'None'}")
        print(f"   Monthly data rows: {len(first_report.get('monthly_data', []))}")
        print(f"   Totals: {first_report.get('totals')}")
        print()

        if first_report.get('monthly_data'):
            print("Sample Monthly Data (first 3 rows):")
            for i, month in enumerate(first_report['monthly_data'][:3]):
                print(f"   Row {i+1}: {month.get('month_name')} - Prestaciones: ${month.get('accumulated_prestaciones', 0):,.2f}")
        else:
            print("   ⚠️  Monthly data is EMPTY!")
    else:
        print("   ⚠️  Reports array is EMPTY!")

except Exception as e:
    print(f"❌ ERROR calling _get_report_values(): {e}")
    import traceback
    traceback.print_exc()

print()
print("="*80)
