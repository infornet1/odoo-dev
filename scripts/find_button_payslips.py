#!/usr/bin/env python3
# Find payslips where Send Mail button should appear

print("=" * 90)
print("PAYSLIPS WHERE 'SEND MAIL' BUTTON SHOULD APPEAR")
print("=" * 90)

# Find payslips with is_send_mail = False
payslips = env['hr.payslip'].search([('is_send_mail', '=', False)], limit=10)

if not payslips:
    print("\n❌ NO payslips found with is_send_mail = False")
    print("\nAll payslips have already been sent via email!")
    print("\nTo test the button:")
    print("  1. Create a new draft payslip, OR")
    print("  2. Reset is_send_mail to False on an existing payslip")
    print("\n   To reset a payslip:")
    print("   >>> slip = env['hr.payslip'].browse(954)")
    print("   >>> slip.write({'is_send_mail': False})")
    print("   >>> env.cr.commit()")
else:
    print(f"\nFound {len(payslips)} payslips where button SHOULD APPEAR:\n")
    print(f"{'ID':<8} {'Number':<20} {'Employee':<30} {'State':<12} {'Date'}")
    print("-" * 90)

    for slip in payslips:
        date_str = slip.date_to.strftime('%Y-%m-%d') if slip.date_to else 'N/A'
        print(f"{slip.id:<8} {slip.number or 'Draft':<20} {slip.employee_id.name:<30} {slip.state:<12} {date_str}")

    print("\n" + "=" * 90)
    print("INSTRUCTIONS TO SEE THE BUTTON:")
    print("=" * 90)
    print(f"1. Go to: Payroll > Payslips")
    print(f"2. Open one of the payslips listed above (e.g., {payslips[0].number or 'ID: ' + str(payslips[0].id)})")
    print(f"3. Clear browser cache: Ctrl+Shift+R")
    print(f"4. Look for 'Send Mail' button in the header (top button area)")
    print(f"5. The button should appear in BLUE (oe_highlight class)")

print("\n" + "=" * 90)
