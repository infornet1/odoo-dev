#!/usr/bin/env python3
# Upgrade hr_payslip_monthly_report module to refresh views

print("Upgrading hr_payslip_monthly_report module...")
print("=" * 80)

module = env['ir.module.module'].search([('name', '=', 'hr_payslip_monthly_report')])

if not module:
    print("❌ Module not found!")
    exit(1)

print(f"Current state: {module.state}")
print(f"Current version: {module.installed_version}")

# Upgrade the module
try:
    module.button_immediate_upgrade()
    print("\n✅ Module upgrade initiated!")
    print("\nPlease:")
    print("  1. Restart Odoo container: docker restart odoo-dev-web")
    print("  2. Clear browser cache (Ctrl+Shift+R)")
    print("  3. Check the payslip form again")
except Exception as e:
    print(f"\n❌ Error upgrading module: {e}")
    print("\nTrying alternative method...")
    try:
        module.button_upgrade()
        env.cr.commit()
        print("✅ Module marked for upgrade!")
        print("\nYou need to:")
        print("  1. Go to Apps menu")
        print("  2. Click 'Apply Scheduled Upgrades'")
        print("  3. Restart Odoo")
    except Exception as e2:
        print(f"❌ Also failed: {e2}")
