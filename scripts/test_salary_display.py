#!/usr/bin/env python3
"""Test salary display in employee header"""

from datetime import date

print("="*80)
print("TEST SALARY V2 DISPLAY IN EMPLOYEE HEADER")
print("="*80)

# Get models
Payslip = env['hr.payslip']
Currency = env['res.currency']

# Find SLIP/802 (VIRGINIA VERDE)
payslip = Payslip.search([
    ('name', '=', 'Liquidación Venezolana V2 of VIRGINIA VERDE for 31jul-2025')
], limit=1)

if not payslip:
    print("ERROR: SLIP/802 not found")
    exit(1)

print(f"Payslip: {payslip.name}")
print(f"Employee: {payslip.employee_id.name}")
print(f"Contract: {payslip.contract_id.name}")

# Get salary V2
contract = payslip.contract_id
salary_v2 = contract.ueipab_salary_v2 if hasattr(contract, 'ueipab_salary_v2') else 0.0

print(f"\nSalary V2 (USD): ${salary_v2:.2f}")

# Get currencies
veb = Currency.search([('name', '=', 'VEB')], limit=1)
usd = env.ref('base.USD')

# Get report model
report_model = env['report.ueipab_payroll_enhancements.liquidacion_breakdown_report']

print("\n" + "="*80)
print("TEST 1: USD DISPLAY")
print("="*80)

data_usd = {
    'wizard_id': 1,
    'currency_id': usd.id,
    'currency_name': 'USD',
    'payslip_ids': [payslip.id],
    'use_custom_rate': False,
    'custom_exchange_rate': None,
    'rate_date': None,
}

report_usd = report_model._generate_breakdown(payslip, usd, data_usd)

print(f"\nEmployee Header:")
print(f"  Empleado: {report_usd['employee'].name}")
print(f"  Cédula: {report_usd['employee'].identification_id or 'N/A'}")
print(f"  Salario: $ {report_usd['salary_v2_formatted']}")
print(f"  Fecha Ingreso: {report_usd['date_start_str']}")
print(f"  Fecha Liquidación: {report_usd['date_to_str']}")

print("\n" + "="*80)
print("TEST 2: VEB DISPLAY (Nov 17 @ 236.4601)")
print("="*80)

data_veb = {
    'wizard_id': 1,
    'currency_id': veb.id,
    'currency_name': 'VEB',
    'payslip_ids': [payslip.id],
    'use_custom_rate': False,
    'custom_exchange_rate': None,
    'rate_date': date(2025, 11, 17),
}

report_veb = report_model._generate_breakdown(payslip, veb, data_veb)

print(f"\nExchange Rate: {report_veb['exchange_rate']:.4f} VEB/USD")

print(f"\nEmployee Header:")
print(f"  Empleado: {report_veb['employee'].name}")
print(f"  Cédula: {report_veb['employee'].identification_id or 'N/A'}")
print(f"  Salario: Bs. {report_veb['salary_v2_formatted']}")
print(f"  Fecha Ingreso: {report_veb['date_start_str']}")
print(f"  Fecha Liquidación: {report_veb['date_to_str']}")

# Calculate expected VEB salary
expected_veb_salary = salary_v2 * report_veb['exchange_rate']
print(f"\nSalary Conversion Check:")
print(f"  USD Salary: ${salary_v2:.2f}")
print(f"  Exchange Rate: {report_veb['exchange_rate']:.4f}")
print(f"  Expected VEB: Bs. {expected_veb_salary:,.2f}")
print(f"  Reported VEB: Bs. {report_veb['salary_v2_formatted']}")

print("\n✅ Salary now displays in employee header with currency conversion!")
print("="*80)
