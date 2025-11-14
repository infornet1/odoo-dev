#!/usr/bin/env python3
"""
Final verification that template is ready after cache clear + restart
"""

print("=" * 80)
print("FINAL TEMPLATE CHECK (after restart)")
print("=" * 80)

# Check template
report_template = env.ref('ueipab_payroll_enhancements.disbursement_detail_doc', raise_if_not_found=False)

if not report_template:
    print("❌ Template not found!")
    exit()

template_arch = report_template.arch_db

# Check for columns
has_salary = '>Salary<' in template_arch
has_bonus = '>Bonus<' in template_arch
has_gross = '>Gross<' in template_arch

print(f"\n📊 Column Headers:")
print(f"   Salary: {'✅ YES' if has_salary else '❌ NO'}")
print(f"   Bonus:  {'✅ YES' if has_bonus else '❌ NO'}")
print(f"   Gross:  {'❌ YES (wrong!)' if has_gross else '✅ NO (correct)'}")

# Check specific calculation lines
uses_deduction_base = 'payslip.contract_id.ueipab_deduction_base' in template_arch
uses_exchange_rate = '* exchange_rate' in template_arch

print(f"\n🔢 Calculations:")
print(f"   Uses contract.ueipab_deduction_base: {'✅ YES' if uses_deduction_base else '❌ NO'}")
print(f"   Multiplies by exchange_rate:         {'✅ YES' if uses_exchange_rate else '❌ NO'}")

# Show a snippet of the Salary column definition
if has_salary:
    # Find the salary header line
    start_idx = template_arch.find('>Salary<')
    snippet = template_arch[max(0, start_idx-100):min(len(template_arch), start_idx+200)]
    print(f"\n📝 Salary Column Snippet:")
    print(f"   ...{snippet}...")

print(f"\n✅ Template is {'READY' if (has_salary and has_bonus and not has_gross) else 'NOT READY'}")

print("\n" + "=" * 80)
print("👉 NOW:")
print("   1. Hard refresh your browser (Ctrl+Shift+R)")
print("   2. Generate USD report again for NOVIEMBRE15-2")
print("   3. Check if Salary/Bonus columns now appear")
print("=" * 80)

