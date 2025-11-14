#!/usr/bin/env python3
"""
Clear all Odoo caches that might prevent template changes from showing
NO DATABASE MODIFICATIONS - just cache clearing
"""

print("=" * 80)
print("CLEARING ALL CACHES")
print("=" * 80)

# 1. Clear web assets cache
print("\n1️⃣ Clearing web assets cache...")
assets = env['ir.attachment'].search([
    '|',
    ('name', 'ilike', 'web.assets%'),
    ('name', 'ilike', '%bundle%')
])
if assets:
    count = len(assets)
    assets.unlink()
    print(f"   ✅ Deleted {count} cached web assets")
else:
    print(f"   ✅ No cached assets found")

# 2. Clear QWeb view cache
print("\n2️⃣ Clearing QWeb view cache...")
env['ir.ui.view'].clear_caches()
print(f"   ✅ QWeb view cache cleared")

# 3. Clear report cache
print("\n3️⃣ Clearing report cache...")
env['ir.actions.report'].clear_caches()
print(f"   ✅ Report cache cleared")

# 4. Force reload of the report template
print("\n4️⃣ Forcing report template reload...")
report_action = env.ref('ueipab_payroll_enhancements.action_report_payroll_disbursement_detail')
if report_action:
    print(f"   Report: {report_action.name}")
    print(f"   Report Name: {report_action.report_name}")
    print(f"   ✅ Report action found")

env.cr.commit()

print("\n" + "=" * 80)
print("✅ ALL CACHES CLEARED")
print("=" * 80)
print("\n👉 NEXT: Restart Odoo container")
print("   Run: docker restart odoo-dev-web")

