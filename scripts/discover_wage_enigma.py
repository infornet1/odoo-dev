#!/usr/bin/env python3
"""
DEEP INVESTIGATION: Discover the wage distribution enigma
Why is Rafael's wage $400.62 but deduction_base only $170.30?
NO DATABASE MODIFICATIONS
"""

batch = env['hr.payslip.run'].search([('name', '=', 'NOVIEMBRE15-2')], limit=1)

# Compare multiple employees to find the pattern
employees_to_check = [
    'ALEJANDRA LOPEZ',  # Standard case
    'RAFAEL PEREZ',     # Has wage gap issue
    'DAVID HERNANDEZ',  # Another case
    'GABRIEL ESPAÑA',   # Another case
]

print("=" * 100)
print("🔍 DEEP INVESTIGATION: Wage Distribution Pattern")
print("=" * 100)

print(f"\n{'Employee':<25} | {'Wage':>12} | {'Deduction Base':>15} | {'Gap':>12} | {'Gap %':>8}")
print("-" * 100)

for emp_name in employees_to_check:
    payslip = env['hr.payslip'].search([
        ('employee_id.name', 'ilike', emp_name),
        ('payslip_run_id', '=', batch.id)
    ], limit=1)
    
    if payslip:
        wage = payslip.contract_id.wage
        deduction_base = payslip.contract_id.ueipab_deduction_base or 0.0
        gap = wage - deduction_base
        gap_pct = (gap / wage * 100) if wage > 0 else 0
        
        print(f"{emp_name:<25} | ${wage:>11,.2f} | ${deduction_base:>14,.2f} | ${gap:>11,.2f} | {gap_pct:>7.1f}%")

# Deep dive into RAFAEL PEREZ contract
print("\n" + "=" * 100)
print("📋 RAFAEL PEREZ - COMPLETE CONTRACT ANALYSIS")
print("=" * 100)

rafael = env['hr.payslip'].search([
    ('employee_id.name', 'ilike', 'RAFAEL PEREZ'),
    ('payslip_run_id', '=', batch.id)
], limit=1)

if rafael:
    contract = rafael.contract_id
    
    print(f"\n👤 Employee: {rafael.employee_id.name}")
    print(f"   Contract: {contract.name}")
    print(f"   State: {contract.state}")
    print(f"   Date Start: {contract.date_start}")
    
    # Check ALL monetary fields in contract
    print(f"\n💰 ALL CONTRACT MONETARY FIELDS:")
    monetary_fields = []
    
    for field_name in contract._fields:
        field = contract._fields[field_name]
        if field.type in ('monetary', 'float'):
            try:
                value = getattr(contract, field_name)
                if value and value != 0:
                    monetary_fields.append((field_name, value))
            except:
                pass
    
    for field_name, value in sorted(monetary_fields, key=lambda x: x[1], reverse=True):
        print(f"   {field_name:<30}: ${value:>12,.2f}")
    
    # Check if there's a wage structure breakdown
    print(f"\n🔍 WAGE STRUCTURE ANALYSIS:")
    wage = contract.wage
    deduction_base = contract.ueipab_deduction_base
    gap = wage - deduction_base
    
    print(f"   Total Wage:          ${wage:>12,.2f} (100.0%)")
    print(f"   Deduction Base:      ${deduction_base:>12,.2f} ({deduction_base/wage*100:>5.1f}%)")
    print(f"   Non-deductible Gap:  ${gap:>12,.2f} ({gap/wage*100:>5.1f}%)")
    
    # Check if gap matches any payslip lines
    print(f"\n🔍 CHECKING IF GAP ($230.32) MATCHES ANY PAYSLIP COMPONENTS:")
    
    # Compare gap against different payslip line combinations
    veb_gross = rafael.line_ids.filtered(lambda l: l.salary_rule_id.code == 'VE_GROSS')
    veb_net = rafael.line_ids.filtered(lambda l: l.salary_rule_id.code == 'VE_NET')
    
    if veb_gross:
        print(f"   VE_GROSS:            ${veb_gross[0].total:>12,.2f} {'❌ Much less' if veb_gross[0].total < gap else '✅ Close!' if abs(veb_gross[0].total - gap) < 1 else '❌ Different'}")
    if veb_net:
        print(f"   VE_NET:              ${veb_net[0].total:>12,.2f} {'❌ Much less' if veb_net[0].total < gap else '✅ Close!' if abs(veb_net[0].total - gap) < 1 else '❌ Different'}")
    
    # Check if gap = wage - deduction_base represents some benefit category
    print(f"\n💡 HYPOTHESIS: The 'gap' ($230.32) might represent:")
    print(f"   - Non-taxable benefits?")
    print(f"   - Housing allowance?")
    print(f"   - Transportation?")
    print(f"   - Other non-deductible compensation?")
    
    # Compare Rafael vs Alejandra structure
    alejandra = env['hr.payslip'].search([
        ('employee_id.name', 'ilike', 'ALEJANDRA LOPEZ'),
        ('payslip_run_id', '=', batch.id)
    ], limit=1)
    
    if alejandra:
        print(f"\n📊 COMPARISON: Rafael vs Alejandra")
        print(f"\n   {'Metric':<35} | {'Rafael':>15} | {'Alejandra':>15} | {'Difference':>15}")
        print("   " + "-" * 85)
        
        a_wage = alejandra.contract_id.wage
        a_deduction_base = alejandra.contract_id.ueipab_deduction_base
        a_gap = a_wage - a_deduction_base
        
        print(f"   {'Wage':<35} | ${wage:>14,.2f} | ${a_wage:>14,.2f} | ${wage - a_wage:>14,.2f}")
        print(f"   {'Deduction Base':<35} | ${deduction_base:>14,.2f} | ${a_deduction_base:>14,.2f} | ${deduction_base - a_deduction_base:>14,.2f}")
        print(f"   {'Gap (wage - deduction_base)':<35} | ${gap:>14,.2f} | ${a_gap:>14,.2f} | ${gap - a_gap:>14,.2f}")
        print(f"   {'Gap as % of Wage':<35} | {gap/wage*100:>14.1f}% | {a_gap/a_wage*100:>14.1f}% | {(gap/wage - a_gap/a_wage)*100:>14.1f}%")
        
        # Check if the percentages are similar
        rafael_gap_pct = gap / wage * 100
        alejandra_gap_pct = a_gap / a_wage * 100
        
        if abs(rafael_gap_pct - alejandra_gap_pct) < 5:
            print(f"\n   ✅ Gap percentage is similar! (~{rafael_gap_pct:.1f}%)")
            print(f"      This suggests a consistent wage structure across employees")
        else:
            print(f"\n   ⚠️  Gap percentage differs significantly!")
            print(f"      Rafael: {rafael_gap_pct:.1f}%, Alejandra: {alejandra_gap_pct:.1f}%")

print("\n" + "=" * 100)
print("🎯 PATTERN ANALYSIS COMPLETE")
print("=" * 100)

