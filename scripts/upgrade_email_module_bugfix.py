#!/usr/bin/env python3
# Upgrade hr_payslip_monthly_report module after bug fix

print("=" * 90)
print("UPGRADING hr_payslip_monthly_report - BUG FIX v17.0.1.1")
print("=" * 90)

module = env['ir.module.module'].search([('name', '=', 'hr_payslip_monthly_report')])

if not module:
    print("❌ Module not found!")
    exit(1)

print(f"\nCurrent state: {module.state}")
print(f"Current version: {module.installed_version}")
print(f"\nBug Fix Details:")
print("  - Removed premature is_send_mail flag setting (line 59)")
print("  - Added mail.compose.message override to set flag AFTER send")
print("  - Button will no longer disappear if user cancels email wizard")

print("\n" + "=" * 90)
print("Initiating module upgrade...")
print("=" * 90)

try:
    module.button_immediate_upgrade()
    print("\n✅ Module upgrade completed successfully!")
    print(f"\nNew version: {module.latest_version}")
except Exception as e:
    print(f"\n❌ Error upgrading module: {e}")
    exit(1)

print("\n" + "=" * 90)
print("NEXT STEPS:")
print("=" * 90)
print("1. Restart Odoo: docker restart odoo-dev-web")
print("2. Clear browser cache: Ctrl+Shift+R")
print("3. Test the fix:")
print("   - Open a payslip")
print("   - Click 'Send Mail' button")
print("   - Cancel the wizard")
print("   - Button should STAY VISIBLE ✅")
print("=" * 90)
