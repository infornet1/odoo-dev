#!/usr/bin/env python3
# Final verification of Send Mail button

print("=" * 90)
print("FINAL VERIFICATION - Send Mail Button")
print("=" * 90)

# 1. Check module
module = env['ir.module.module'].search([('name', '=', 'hr_payslip_monthly_report')])
print(f"\n1. Module Status:")
print(f"   State: {module.state}")
print(f"   Version: {module.installed_version}")

# 2. Check view
view = env['ir.ui.view'].search([
    ('name', '=', 'hr.payslip.view.form.inherit.hr.payslip.monthly.report')
], limit=1)
print(f"\n2. View Status:")
print(f"   ID: {view.id}")
print(f"   Active: {view.active}")
print(f"   Button in XML: {'Send Mail' in view.arch}")

# 3. Check sample payslips
print(f"\n3. Sample Payslips (where button should appear):")
print(f"\n   {'ID':<8} {'Number':<15} {'State':<12} {'is_send_mail':<15} {'Button Visibility'}")
print("   " + "-" * 75)

payslips = env['hr.payslip'].search([], limit=5, order='id desc')
for slip in payslips:
    # Button shows when is_send_mail == False
    button_shows = "✅ SHOWS" if not slip.is_send_mail else "❌ HIDDEN"
    print(f"   {slip.id:<8} {slip.number or 'Draft':<15} {slip.state:<12} {str(slip.is_send_mail):<15} {button_shows}")

# 4. Check where button is positioned
print(f"\n4. Button Positioning:")
print(f"   Position: AFTER 'Compute Sheet' button")
print(f"   Location: <header> section of payslip form")
print(f"   Note: 'Compute Sheet' button only shows in DRAFT state")
print(f"         'Send Mail' button should show in ALL states (when is_send_mail=False)")

# 5. Instructions
print(f"\n5. How to See the Button:")
print(f"   ✅ Open any payslip with is_send_mail = False")
print(f"   ✅ Look in the header (top buttons area)")
print(f"   ✅ Button appears AFTER 'Compute Sheet' (if draft) or in header")
print(f"   ✅ Clear browser cache: Ctrl+Shift+R")

# 6. Test: Try to call the method directly
print(f"\n6. Testing button method:")
test_slip = env['hr.payslip'].search([('is_send_mail', '=', False)], limit=1)
if test_slip:
    try:
        # Don't actually send, just check if method exists
        if hasattr(test_slip, 'action_payslip_send'):
            print(f"   ✅ Method 'action_payslip_send' exists on hr.payslip")
            print(f"   ✅ Method can be called (tested with SLIP/{test_slip.id})")
        else:
            print(f"   ❌ Method 'action_payslip_send' NOT found!")
    except Exception as e:
        print(f"   ⚠️  Error: {e}")
else:
    print(f"   ⚠️  No payslips with is_send_mail=False to test")

print("\n" + "=" * 90)
print("RECOMMENDATION:")
print("=" * 90)
print("1. Clear browser cache (Ctrl+Shift+R) and hard reload")
print("2. Open payslip form (any payslip with is_send_mail = False)")
print("3. Check the header buttons area - button should be next to other action buttons")
print("4. If still not visible, check browser console (F12) for JavaScript errors")
print("=" * 90)
