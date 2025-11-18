#!/usr/bin/env python3
"""Test wizard data passing"""

from datetime import date

print("="*80)
print("TEST WIZARD DATA PASSING")
print("="*80)

# Create a test wizard
Wizard = env['liquidacion.breakdown.wizard']
Payslip = env['hr.payslip']
Currency = env['res.currency']

# Find a liquidation payslip
payslip = Payslip.search([
    ('struct_id.code', '=', 'LIQUID_VE_V2')
], limit=1, order='id desc')

if not payslip:
    print("No liquidation payslip found")
    exit(1)

print(f"Test Payslip: {payslip.name}")
print(f"Employee: {payslip.employee_id.name}")

# Get VEB currency
veb = Currency.search([('name', '=', 'VEB')], limit=1)

print(f"\nCreating wizard with:")
print(f"  - Payslip: {payslip.name}")
print(f"  - Currency: VEB")
print(f"  - Rate Date: 2025-11-17")

# Create wizard
wizard = Wizard.create({
    'payslip_ids': [(6, 0, [payslip.id])],
    'currency_id': veb.id,
    'rate_date': '2025-11-17',
    'use_custom_rate': False,
})

print(f"\nWizard created:")
print(f"  ID: {wizard.id}")
print(f"  Currency: {wizard.currency_id.name}")
print(f"  Rate Date: {wizard.rate_date}")
print(f"  Use Custom Rate: {wizard.use_custom_rate}")

# Simulate action_print_pdf data preparation
data = {
    'wizard_id': wizard.id,
    'currency_id': wizard.currency_id.id,
    'currency_name': wizard.currency_id.name,
    'payslip_ids': wizard.payslip_ids.ids,
    'use_custom_rate': wizard.use_custom_rate,
    'custom_exchange_rate': wizard.custom_exchange_rate if wizard.use_custom_rate else None,
    'rate_date': wizard.rate_date,
}

print(f"\nData dict that will be passed to report:")
for key, value in data.items():
    print(f"  {key}: {value} (type: {type(value).__name__})")

print("\n" + "="*80)
print("SIMULATING REPORT GENERATION")
print("="*80)

# Simulate what happens in report
custom_date_raw = data.get('rate_date')
print(f"\nRaw rate_date from data: {custom_date_raw} (type: {type(custom_date_raw).__name__})")

# Convert custom_date from string to date object if needed
custom_date = None
if custom_date_raw:
    if isinstance(custom_date_raw, str):
        from datetime import datetime
        try:
            custom_date = datetime.strptime(custom_date_raw, '%Y-%m-%d').date()
            print(f"✅ Converted to date: {custom_date}")
        except Exception as e:
            print(f"❌ Conversion failed: {e}")
            custom_date = None
    else:
        custom_date = custom_date_raw
        print(f"✅ Already date object: {custom_date}")

print(f"\nFinal custom_date for lookup: {custom_date}")

# Now test the lookup
if custom_date:
    CurrencyRate = env['res.currency.rate']
    rate_record = CurrencyRate.search([
        ('currency_id', '=', veb.id),
        ('name', '<=', custom_date)
    ], limit=1, order='name desc')
    
    if rate_record:
        if hasattr(rate_record, 'company_rate'):
            exchange_rate = rate_record.company_rate
        elif rate_record.rate > 0:
            exchange_rate = 1.0 / rate_record.rate
        else:
            exchange_rate = 1.0
            
        print(f"\n✅ Exchange rate found: {exchange_rate:.4f} VEB/USD")
        print(f"   Rate date: {rate_record.name}")
    else:
        print(f"\n❌ No rate found for {custom_date}")

print("="*80)
