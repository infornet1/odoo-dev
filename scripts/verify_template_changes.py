#!/usr/bin/env python3
"""
Verify that the template changes are loaded in Odoo
NO DATABASE MODIFICATIONS - just checking template
"""

# Check if the report template view exists and has the correct structure
report_template = env.ref('ueipab_payroll_enhancements.disbursement_detail_doc', raise_if_not_found=False)

if not report_template:
    print("❌ Report template not found in database")
    exit()

print("=" * 80)
print("TEMPLATE VERIFICATION")
print("=" * 80)

print(f"\n📄 Template ID: {report_template.id}")
print(f"   Name: disbursement_detail_doc")

# Check the template arch (XML structure)
template_arch = report_template.arch_db

# Check for new columns
has_salary_column = 'Salary' in template_arch and '>Salary<' in template_arch
has_bonus_column = 'Bonus' in template_arch and '>Bonus<' in template_arch
has_gross_column = 'Gross' in template_arch or '>Gross<' in template_arch

print(f"\n🔍 Column Headers Check:")
print(f"   'Salary' column: {'✅ FOUND' if has_salary_column else '❌ NOT FOUND'}")
print(f"   'Bonus' column:  {'✅ FOUND' if has_bonus_column else '❌ NOT FOUND'}")
print(f"   'Gross' column:  {'❌ FOUND (should be removed!)' if has_gross_column else '✅ NOT FOUND (correct)'}")

# Check for contract field usage
has_deduction_base = 'ueipab_deduction_base' in template_arch
has_contract_wage = 'contract_id.wage' in template_arch

print(f"\n🔍 Contract Field Usage:")
print(f"   Uses 'ueipab_deduction_base': {'✅ YES' if has_deduction_base else '❌ NO'}")
print(f"   Uses 'contract_id.wage':      {'✅ YES' if has_contract_wage else '❌ NO'}")

# Check for exchange_rate multiplication
has_exchange_rate = 'exchange_rate' in template_arch

print(f"\n🔍 Currency Conversion:")
print(f"   Uses 'exchange_rate' variable: {'✅ YES' if has_exchange_rate else '❌ NO'}")

# Check module version
module = env['ir.module.module'].search([('name', '=', 'ueipab_payroll_enhancements')], limit=1)
print(f"\n📦 Module Status:")
print(f"   State: {module.state}")
print(f"   Installed Version: {module.installed_version or 'Unknown'}")

if module.state == 'to upgrade':
    print(f"\n⚠️  MODULE NEEDS UPGRADE!")
    print(f"   The template changes are in the file but not loaded in database")
    print(f"   Action required: Upgrade module")
elif not (has_salary_column and has_bonus_column):
    print(f"\n⚠️  TEMPLATE STRUCTURE ISSUE!")
    print(f"   Module is installed but template doesn't have Salary/Bonus columns")
    print(f"   Action required: Upgrade module to reload template")
else:
    print(f"\n✅ Template structure looks correct!")

# Check web assets cache
asset_count = env['ir.attachment'].search_count([
    ('name', 'ilike', 'web.assets%'),
    ('res_model', '=', 'ir.ui.view')
])

print(f"\n🗂️  Web Assets Cache:")
print(f"   Cached assets: {asset_count} files")
if asset_count > 50:
    print(f"   ⚠️  Large cache - may need clearing for UI changes to appear")

print("\n" + "=" * 80)

