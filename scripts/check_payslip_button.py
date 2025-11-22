#!/usr/bin/env python3
# Check payslip records to see is_send_mail values

payslips = env['hr.payslip'].search([], limit=10, order='id desc')

print(f"Found {len(payslips)} recent payslips:\n")
print(f"{'ID':<10} {'Number':<15} {'Employee':<25} {'State':<10} {'is_send_mail'}")
print("=" * 90)

for slip in payslips:
    print(f"{slip.id:<10} {slip.number or 'Draft':<15} {slip.employee_id.name:<25} {slip.state:<10} {slip.is_send_mail}")

print("\n" + "=" * 90)
print("\nButton visibility logic:")
print("  Button shows when: is_send_mail == False")
print("  Button hidden when: is_send_mail == True")
print("\nPayslips where button SHOULD appear:")
false_count = len([s for s in payslips if not s.is_send_mail])
print(f"  {false_count} payslips have is_send_mail = False")

# Check if there are any view inheritance conflicts
print("\n" + "=" * 90)
print("Checking for view conflicts...")
views = env['ir.ui.view'].search([
    ('model', '=', 'hr.payslip'),
    ('type', '=', 'form'),
    ('active', '=', True)
])

print(f"\nFound {len(views)} active form views for hr.payslip:")
for view in views:
    if 'inherit' in view.name.lower() or view.inherit_id:
        mode = view.mode or 'primary'
        print(f"  - {view.name} (ID: {view.id}, mode: {mode})")
        if view.inherit_id:
            print(f"    Inherits from: {view.inherit_id.name}")
