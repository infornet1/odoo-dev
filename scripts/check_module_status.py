#!/usr/bin/env python3
# Check hr_payslip_monthly_report module status

# Get module
module = env['ir.module.module'].search([('name', '=', 'hr_payslip_monthly_report')])

if not module:
    print("❌ Module NOT found in database")
    exit(1)

print(f"Module: {module.name}")
print(f"State: {module.state}")
print(f"Installed Version: {module.installed_version}")
print(f"Latest Version: {module.latest_version}")
print(f"Demo: {module.demo}")
print(f"Published Version: {module.published_version}")
print("")

# Check dependencies
print("Dependencies:")
deps = env['ir.module.module.dependency'].search([('module_id', '=', module.id)])
for dep in deps:
    dep_module = env['ir.module.module'].search([('name', '=', dep.name)])
    if dep_module:
        print(f"  - {dep.name}: {dep_module.state}")
    else:
        print(f"  - {dep.name}: ❌ NOT FOUND")

print("")

# Check if views are loaded
views = env['ir.ui.view'].search([('model', '=', 'hr.payslip'), ('name', 'ilike', 'monthly')])
print(f"Views found: {len(views)}")
for view in views:
    print(f"  - {view.name} (ID: {view.id})")
    print(f"    Inherit ID: {view.inherit_id.name if view.inherit_id else 'None'}")
    print(f"    Active: {view.active}")

print("")

# Check if field exists on model
payslip = env['hr.payslip'].search([], limit=1)
if payslip:
    print(f"Sample payslip: {payslip.number}")
    print(f"Has is_send_mail field: {hasattr(payslip, 'is_send_mail')}")
    if hasattr(payslip, 'is_send_mail'):
        print(f"is_send_mail value: {payslip.is_send_mail}")
