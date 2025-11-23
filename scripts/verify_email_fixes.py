#!/usr/bin/env python3
"""
Verify that all 3 email issues are resolved:
1. Email template variables render correctly
2. PDF report generates with data (not blank)
3. Accounting validation passes
"""

print("=" * 80)
print("EMAIL FUNCTIONALITY VERIFICATION")
print("=" * 80)

# Get the NOVIEMBRE15-SOLO batch
HrPayslipRun = env['hr.payslip.run']
batch = HrPayslipRun.search([('name', '=', 'NOVIEMBRE15-SOLO')], limit=1)

if not batch:
    print("\n❌ Batch 'NOVIEMBRE15-SOLO' not found")
    exit()

print(f"\n✅ Found batch: {batch.name}")
print(f"   Payslips in batch: {len(batch.slip_ids)}")

# Test Issue 1: Email Template Rendering
print("\n" + "=" * 80)
print("ISSUE 1: Email Template Variable Rendering")
print("=" * 80)

template = env.ref('ueipab_payroll_enhancements.email_template_edi_payslip_compact', raise_if_not_found=False)

if not template:
    print("\n❌ Email template not found")
else:
    print(f"\n✅ Template found: {template.name}")

    # Check template syntax
    if '${' in template.body_html and 'object.employee_id.name' in template.body_html:
        print("✅ Template uses correct ${} syntax")
    elif '{{' in template.body_html:
        print("❌ Template still uses {{ }} syntax (WRONG)")
    else:
        print("⚠️  Template syntax unclear")

    # Test rendering for first payslip
    if batch.slip_ids:
        test_slip = batch.slip_ids[0]
        try:
            rendered = template._render_field('body_html', [test_slip.id])[test_slip.id]

            # Check if variables were replaced
            if '${' not in rendered and test_slip.employee_id.name in rendered:
                print(f"✅ Variables render correctly (employee: {test_slip.employee_id.name})")
            else:
                print("❌ Variables not rendering")
                if '${' in rendered[:200]:
                    print(f"   Raw template text found: {rendered[:200]}")
        except Exception as e:
            print(f"❌ Rendering error: {str(e)}")

# Test Issue 2: PDF Report Generation
print("\n" + "=" * 80)
print("ISSUE 2: PDF Report Data (DEVENGOS/DEDUCCIONES)")
print("=" * 80)

PayslipCompactReport = env['report.ueipab_payroll_enhancements.report_payslip_compact']

if batch.slip_ids:
    test_slip = batch.slip_ids[0]

    try:
        # Call report model without wizard data (like email does)
        report_data = PayslipCompactReport._get_report_values([test_slip.id], data=None)

        print(f"\n✅ Report data generated for {test_slip.employee_id.name}")

        # Check currency default
        if report_data.get('currency'):
            print(f"✅ Currency defaulted to: {report_data['currency'].name}")
        else:
            print("❌ No currency in report data")

        # Check reports list
        if report_data.get('reports'):
            report = report_data['reports'][0]

            earnings_count = len(report.get('earnings', []))
            deductions_count = len(report.get('deductions', []))

            print(f"✅ Earnings lines: {earnings_count}")
            print(f"✅ Deductions lines: {deductions_count}")

            if earnings_count > 0 and deductions_count > 0:
                print("✅ PDF will have data (not blank)")
            else:
                print("❌ PDF sections will be blank")
        else:
            print("❌ No report data generated")

    except Exception as e:
        print(f"❌ Report generation error: {str(e)}")

# Test Issue 3: Accounting Validation
print("\n" + "=" * 80)
print("ISSUE 3: Accounting Configuration (Debit/Credit)")
print("=" * 80)

SalaryRule = env['hr.salary.rule']

# Check V2 rules used by batch
v2_rules = SalaryRule.search([
    '|', ('code', 'like', '_V2'),
    ('code', 'like', 'LIQUID_%')
])

missing_config = []
for rule in v2_rules:
    if not rule.account_debit_id or not rule.account_credit_id:
        missing_config.append(rule)

if missing_config:
    print(f"\n❌ {len(missing_config)} rules still missing accounting:")
    for rule in missing_config:
        print(f"   - [{rule.code}] {rule.name}")
else:
    print(f"\n✅ All {len(v2_rules)} V2 rules have accounting configured")
    print("\nPayroll rules (sample):")
    payroll_rule = SalaryRule.search([('code', '=', 'VE_SALARY_V2')], limit=1)
    if payroll_rule and payroll_rule.account_debit_id:
        print(f"   VE_SALARY_V2: {payroll_rule.account_debit_id.code} / {payroll_rule.account_credit_id.code}")

    print("\nLiquidation rules (sample):")
    liquid_rule = SalaryRule.search([('code', '=', 'LIQUID_NET_V2')], limit=1)
    if liquid_rule and liquid_rule.account_debit_id:
        print(f"   LIQUID_NET_V2: {liquid_rule.account_debit_id.code} / {liquid_rule.account_credit_id.code}")

print("\n" + "=" * 80)
print("VERIFICATION COMPLETE")
print("=" * 80)
