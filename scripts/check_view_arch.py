#!/usr/bin/env python3
# Check the actual compiled view architecture

# Get the inherited view
view = env['ir.ui.view'].search([
    ('name', '=', 'hr.payslip.view.form.inherit.hr.payslip.monthly.report')
], limit=1)

if not view:
    print("❌ View NOT found")
    exit(1)

print(f"View: {view.name}")
print(f"ID: {view.id}")
print(f"Active: {view.active}")
print(f"Inherit ID: {view.inherit_id.name if view.inherit_id else 'None'}")
print(f"Mode: {view.mode}")
print("")
print("=" * 80)
print("VIEW ARCH (from database):")
print("=" * 80)
print(view.arch)
print("")
print("=" * 80)

# Get the base view to see the full compiled output
print("\nGetting full compiled view...")
base_view = env['ir.ui.view'].search([
    ('model', '=', 'hr.payslip'),
    ('type', '=', 'form'),
    ('name', '=', 'hr.payslip.view.form')
], limit=1)

if base_view:
    print(f"\nBase view: {base_view.name}")
    # Get combined view
    try:
        combined_arch = env['ir.ui.view'].with_context({}).get_combined_arch()
        print("\nSearching for 'Send Mail' button in combined arch...")
        if 'Send Mail' in str(combined_arch):
            print("✅ 'Send Mail' button found in combined view!")
        else:
            print("❌ 'Send Mail' button NOT found in combined view")
    except:
        print("Could not get combined arch")

# Check for xpath issues
print("\nChecking xpath target...")
if 'action_compute_sheet' in view.arch:
    print("✅ xpath target 'action_compute_sheet' referenced in view arch")
else:
    print("❌ xpath target 'action_compute_sheet' NOT in view arch")

if 'action_payslip_send' in view.arch:
    print("✅ 'action_payslip_send' method found in view arch")
else:
    print("❌ 'action_payslip_send' method NOT in view arch")

if 'Send Mail' in view.arch:
    print("✅ 'Send Mail' button text found in view arch")
else:
    print("❌ 'Send Mail' button text NOT in view arch")
